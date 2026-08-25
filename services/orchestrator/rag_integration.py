"""
RAG (Retrieval-Augmented Generation) Integration for FuzeAgent
Handles vector embeddings, similarity search, and context retrieval for AI agents
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
from chromadb.config import Settings
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from knowledge_manager import DocumentMetadata, knowledge_manager

logger = logging.getLogger(__name__)

# ChromaDB configuration.
#
# THREE DEFECTS LIVED IN THIS BLOCK AND THE CONNECT BELOW, and together they made
# RAG inert in production while every log line, probe and endpoint looked healthy:
#
#   1. CHROMA_HOST defaulted to "localhost" and NOTHING set it in any deployment
#      manifest, so the pod dialled itself.
#   2. chroma_client_auth_provider was the literal "basic". Chroma resolves that
#      string as an import path to a provider class, so "basic" resolves to
#      nothing — the client was built with no auth while appearing to configure it.
#   3. chroma_client_auth_credentials was a hardcoded "". Even with (2) fixed,
#      it would have authenticated with an empty secret.
#
# Any of the three raises inside _initialize_components, whose broad `except`
# then set collection = None — after which every search returned an empty result
# that no caller could distinguish from an empty corpus.
#
# The provider strings are kept in ONE place so the literal cannot be re-typed.
# agent-templates/a2a/rag/config.py carries the same two constants for the shared
# A2A image, and tests/test_rag_provider_parity.py fails if the two disagree.
TOKEN_AUTH_PROVIDER = "chromadb.auth.token_authn.TokenAuthClientProvider"  # nosec B105 -- an import path Chroma resolves to a class, not a credential; B105 fires on the "TOKEN" in the variable NAME. The real credential is read from CHROMA_AUTH_TOKEN at runtime and never appears in this file.
BASIC_AUTH_PROVIDER = "chromadb.auth.basic_authn.BasicAuthClientProvider"

CHROMA_HOST = os.environ.get("CHROMA_HOST", "").strip()
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
CHROMA_COLLECTION_NAME = "fuzeagent_knowledge"


class RAGUnavailable(RuntimeError):
    """The vector store is not reachable or not configured.

    Raised rather than degraded. "RAG is down" and "the corpus has nothing on
    that" are different answers and a caller must be able to tell them apart —
    conflating them is what hid this outage.
    """


def _chroma_settings():
    """Auth settings for the client, or None when explicitly unauthenticated."""
    token = os.environ.get("CHROMA_AUTH_TOKEN", "").strip()
    basic = os.environ.get("CHROMA_AUTH_BASIC", "").strip()
    if token and basic:
        raise RAGUnavailable("Both CHROMA_AUTH_TOKEN and CHROMA_AUTH_BASIC are set.")
    if token:
        return Settings(
            chroma_client_auth_provider=TOKEN_AUTH_PROVIDER,
            chroma_client_auth_credentials=token,
            chroma_auth_token_transport_header=os.environ.get(
                "CHROMA_AUTH_HEADER", "Authorization"
            ),
        )
    if basic:
        if ":" not in basic:
            raise RAGUnavailable("CHROMA_AUTH_BASIC must be 'user:password'.")
        return Settings(
            chroma_client_auth_provider=BASIC_AUTH_PROVIDER,
            chroma_client_auth_credentials=basic,
        )
    if os.environ.get("CHROMA_ALLOW_UNAUTHENTICATED", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return Settings()
    raise RAGUnavailable(
        "No Chroma credential configured. Set CHROMA_AUTH_TOKEN (preferred) or "
        "CHROMA_AUTH_BASIC, or set CHROMA_ALLOW_UNAUTHENTICATED=1 to state that "
        "this instance has no auth. An empty credential is never assumed to mean "
        "'no auth wanted'."
    )


# Embedding model configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Lightweight, fast model
CHUNK_SIZE = 512  # Characters per chunk
CHUNK_OVERLAP = 50  # Character overlap between chunks


class DocumentChunk(BaseModel):
    """Document chunk for vector storage"""

    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_vector: Optional[List[float]] = None


class RAGContext(BaseModel):
    """Context retrieved for RAG"""

    query: str
    relevant_chunks: List[DocumentChunk]
    similarity_scores: List[float]
    total_documents: int
    context_length: int


class RAGIntegration:
    """RAG system integration"""

    def __init__(self):
        """Initialize RAG system"""
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        # Retained, not discarded. This module is imported at process start and a
        # raise here would take down the whole orchestrator, so construction stays
        # tolerant — but the reason is kept and every query re-raises it, so the
        # failure surfaces at the first use instead of never.
        self.init_error: Optional[str] = None
        self._initialize_components()

    @property
    def is_available(self) -> bool:
        return bool(self.embedding_model and self.collection)

    def _initialize_components(self):
        """Initialize embedding model and vector database"""
        try:
            # Initialize embedding model
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")

            # Initialize ChromaDB client
            if not CHROMA_HOST:
                raise RAGUnavailable(
                    "CHROMA_HOST is unset. Refusing to fall back to localhost: a pod "
                    "that dials itself connects to nothing and then reports an empty "
                    "corpus forever, which is exactly how this went unnoticed."
                )
            logger.info(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
            self.chroma_client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=CHROMA_PORT,
                ssl=os.environ.get("CHROMA_SSL", "0").strip().lower()
                in {"1", "true", "yes", "on"},
                settings=_chroma_settings(),
            )

            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(
                    name=CHROMA_COLLECTION_NAME
                )
                logger.info(
                    f"Connected to existing collection: {CHROMA_COLLECTION_NAME}"
                )
            except Exception:
                self.collection = self.chroma_client.create_collection(
                    name=CHROMA_COLLECTION_NAME,
                    metadata={"description": "FuzeAgent knowledge base documents"},
                )
                logger.info(f"Created new collection: {CHROMA_COLLECTION_NAME}")

        except Exception as e:
            # The error is RECORDED, not just logged and dropped. `init_error` is
            # what search_relevant_context re-raises, and what /rag/status reports.
            self.init_error = f"{type(e).__name__}: {e}"
            logger.error("RAG unavailable: %s", self.init_error)
            self.embedding_model = None
            self.chroma_client = None
            self.collection = None

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding"""
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + CHUNK_SIZE

            # Try to find a good breaking point (sentence/paragraph end)
            if end < len(text):
                # Look for sentence endings within the next 100 characters
                for i in range(end, min(end + 100, len(text))):
                    if text[i] in ".!?\n":
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + CHUNK_SIZE - CHUNK_OVERLAP, end)

        return chunks

    async def index_document(self, document: DocumentMetadata) -> bool:
        """Index a document for RAG retrieval"""
        if not self.embedding_model or not self.collection:
            logger.error("RAG system not properly initialized")
            return False

        try:
            # Check if document already indexed
            existing = self.collection.get(where={"document_id": document.id})

            if existing["documents"]:
                logger.info(f"Document {document.id} already indexed, updating...")
                await self.remove_document_from_index(document.id)

            # Get document content
            content = document.extracted_text
            if not content:
                logger.warning(f"No content to index for document {document.id}")
                return False

            # Split into chunks
            text_chunks = self._chunk_text(content)
            if not text_chunks:
                logger.warning(f"No chunks generated for document {document.id}")
                return False

            # Generate embeddings for chunks
            logger.info(f"Generating embeddings for {len(text_chunks)} chunks")
            embeddings = self.embedding_model.encode(text_chunks).tolist()

            # Prepare data for ChromaDB
            chunk_ids = []
            metadatas = []

            for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
                chunk_id = f"{document.id}_{i}"
                chunk_ids.append(chunk_id)

                metadata = {
                    "document_id": document.id,
                    "document_title": document.title,
                    "document_type": document.type,
                    "chunk_index": i,
                    "organization_id": document.organization_id or "",
                    "team_id": document.team_id or "",
                    "agent_id": document.agent_id or "",
                    "upload_date": document.upload_date.isoformat(),
                    "tags": json.dumps(document.tags),
                    "source_url": document.source_url or "",
                    "word_count": len(chunk.split()),
                }
                metadatas.append(metadata)

            # Add to ChromaDB collection
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=text_chunks,
                metadatas=metadatas,
            )

            logger.info(
                f"Successfully indexed document {document.id} with {len(text_chunks)} chunks"
            )
            return True

        except Exception as e:
            logger.error(f"Error indexing document {document.id}: {e}")
            return False

    async def remove_document_from_index(self, document_id: str) -> bool:
        """Remove document from RAG index"""
        if not self.collection:
            logger.error("RAG system not properly initialized")
            return False

        try:
            # Get existing chunks for this document
            existing = self.collection.get(where={"document_id": document_id})

            if existing["ids"]:
                self.collection.delete(ids=existing["ids"])
                logger.info(
                    f"Removed {len(existing['ids'])} chunks for document {document_id}"
                )

            return True

        except Exception as e:
            logger.error(f"Error removing document {document_id} from index: {e}")
            return False

    async def search_relevant_context(
        self,
        query: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
        max_results: int = 5,
        similarity_threshold: float = 0.7,
    ) -> RAGContext:
        """Search for relevant context based on query"""
        if not self.is_available:
            # RAISES. Returning an empty RAGContext here is the original defect:
            # it is a well-formed "we found nothing" answer, and a caller — human
            # or agent — has no way to know the store was never reached.
            raise RAGUnavailable(self.init_error or "RAG system was not initialized")

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]

            # Build where filter based on scope
            where_filter = {}
            if agent_id:
                where_filter["agent_id"] = agent_id
            elif team_id:
                where_filter["team_id"] = team_id
            elif organization_id:
                where_filter["organization_id"] = organization_id

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"],
            )

            relevant_chunks = []
            similarity_scores = []

            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]

                for doc, metadata, distance in zip(documents, metadatas, distances):
                    # Convert distance to similarity (ChromaDB uses cosine distance)
                    similarity = 1.0 - distance

                    if similarity >= similarity_threshold:
                        chunk = DocumentChunk(
                            id=f"{metadata['document_id']}_{metadata['chunk_index']}",
                            document_id=metadata["document_id"],
                            chunk_index=metadata["chunk_index"],
                            content=doc,
                            metadata=metadata,
                        )
                        relevant_chunks.append(chunk)
                        similarity_scores.append(similarity)

            # Calculate total context length
            context_length = sum(len(chunk.content) for chunk in relevant_chunks)

            logger.info(
                f"Found {len(relevant_chunks)} relevant chunks for query: '{query[:50]}...'"
            )

            return RAGContext(
                query=query,
                relevant_chunks=relevant_chunks,
                similarity_scores=similarity_scores,
                total_documents=len(
                    set(chunk.document_id for chunk in relevant_chunks)
                ),
                context_length=context_length,
            )

        except Exception as e:
            logger.error(f"Error searching for relevant context: {e}")
            return RAGContext(
                query=query,
                relevant_chunks=[],
                similarity_scores=[],
                total_documents=0,
                context_length=0,
            )

    async def get_contextual_prompt(
        self,
        user_message: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
        max_context_length: int = 4000,
    ) -> str:
        """Generate a contextually enhanced prompt using RAG"""

        # Search for relevant context
        rag_context = await self.search_relevant_context(
            query=user_message,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            max_results=10,
        )

        if not rag_context.relevant_chunks:
            return user_message

        # Build context from relevant chunks
        context_parts = []
        current_length = 0

        for i, chunk in enumerate(rag_context.relevant_chunks):
            chunk_text = f"[Document: {chunk.metadata.get('document_title', 'Unknown')}]\n{chunk.content}\n"

            if current_length + len(chunk_text) > max_context_length:
                break

            context_parts.append(chunk_text)
            current_length += len(chunk_text)

        if not context_parts:
            return user_message

        # Build enhanced prompt
        context_section = "\n---\n".join(context_parts)

        enhanced_prompt = f"""You have access to the following relevant information from the knowledge base:

{context_section}

---

Based on the above context and your general knowledge, please respond to the following:

{user_message}

If the context contains relevant information, please use it in your response. If not, respond based on your general knowledge."""

        logger.info(
            f"Enhanced prompt with {len(rag_context.relevant_chunks)} relevant chunks ({current_length} chars)"
        )

        return enhanced_prompt

    async def index_all_documents(
        self, organization_id: str = None, team_id: str = None, agent_id: str = None
    ) -> Dict[str, int]:
        """Index all documents in a scope"""
        if not self.embedding_model or not self.collection:
            logger.error("RAG system not properly initialized")
            return {"indexed": 0, "failed": 0, "skipped": 0}

        try:
            # Get all documents in scope
            documents = await knowledge_manager.get_documents(
                organization_id=organization_id, team_id=team_id, agent_id=agent_id
            )

            indexed = 0
            failed = 0
            skipped = 0

            for document in documents:
                try:
                    if document.status == "active" and document.extracted_text:
                        success = await self.index_document(document)
                        if success:
                            indexed += 1
                        else:
                            failed += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Error indexing document {document.id}: {e}")
                    failed += 1

            logger.info(
                f"Indexing complete: {indexed} indexed, {failed} failed, {skipped} skipped"
            )

            return {"indexed": indexed, "failed": failed, "skipped": skipped}

        except Exception as e:
            logger.error(f"Error in bulk indexing: {e}")
            return {"indexed": 0, "failed": 0, "skipped": 0}

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG index"""
        if not self.collection:
            return {
                "total_chunks": 0,
                "total_documents": 0,
                "organizations": 0,
                "teams": 0,
                "agents": 0,
            }

        try:
            # Get collection count
            count = self.collection.count()

            # Get sample data to analyze
            sample = self.collection.get(limit=1000, include=["metadatas"])

            unique_documents = set()
            unique_orgs = set()
            unique_teams = set()
            unique_agents = set()

            if sample["metadatas"]:
                for metadata in sample["metadatas"]:
                    unique_documents.add(metadata.get("document_id", ""))
                    if metadata.get("organization_id"):
                        unique_orgs.add(metadata["organization_id"])
                    if metadata.get("team_id"):
                        unique_teams.add(metadata["team_id"])
                    if metadata.get("agent_id"):
                        unique_agents.add(metadata["agent_id"])

            return {
                "total_chunks": count,
                "total_documents": len(unique_documents),
                "organizations": len(unique_orgs),
                "teams": len(unique_teams),
                "agents": len(unique_agents),
                "model": EMBEDDING_MODEL,
                "chunk_size": CHUNK_SIZE,
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {
                "total_chunks": 0,
                "total_documents": 0,
                "organizations": 0,
                "teams": 0,
                "agents": 0,
                "error": str(e),
            }


# Global RAG integration instance
rag_system = RAGIntegration()
