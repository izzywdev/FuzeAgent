"""
rag_integration.py
Consolidated RAG (Retrieval-Augmented Generation) & GraphRAG Integration for FuzeAgent.
Standardized entirely on PostgreSQL pgvector(384) with FuzeInfra Neo4j Knowledge Graph traversal.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from knowledge_manager import DocumentMetadata, knowledge_manager
from brain_store import (
    add_document_chunks,
    add_document,
    search_multi_brains,
    search,
    get_agent_brains,
    get_hierarchical_context_for_agent,
)
from graph_client import brain_graph
from s3_storage import s3_storage
from kafka_pipeline import brain_pipeline

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dimensional dense vectors
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
    graph_context: Optional[List[str]] = None
    distilled_prompt: Optional[str] = None


class RAGIntegration:
    """Consolidated pgvector and GraphRAG Integration"""

    def __init__(self):
        self.embedding_model = None
        self._initialize_components()

    def _initialize_components(self):
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("SentenceTransformer loaded. Vector store consolidated on PostgreSQL pgvector(384).")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None

    def _chunk_text(self, text: str) -> List[str]:
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + CHUNK_SIZE
            if end < len(text):
                break_point = -1
                for punct in [".\n", ".\r\n", ". ", "\n\n", "? ", "! ", "\n"]:
                    pos = text.rfind(punct, start, end)
                    if pos != -1 and pos > start + CHUNK_SIZE // 2:
                        break_point = pos + len(punct)
                        break

                if break_point != -1:
                    end = break_point

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - CHUNK_OVERLAP
            if start >= len(text) or end >= len(text):
                break

        return chunks

    async def index_document(self, document: DocumentMetadata, brain_id: Optional[str] = None) -> bool:
        """
        Splits document into chunks, embeds via sentence-transformers,
        and saves into PostgreSQL brain_chunks & brain_documents.
        Also publishes Kafka events for background graph sync.
        """
        try:
            target_brain_id = brain_id or f"brain_agent_{document.agent_id}" if document.agent_id else "brain_org_global"
            content = document.extracted_text
            if not content:
                logger.warning(f"No content to index for document {document.id}")
                return False

            text_chunks = self._chunk_text(content)
            if not text_chunks:
                logger.warning(f"No chunks generated for document {document.id}")
                return False

            chunk_records = []
            for i, chunk_txt in enumerate(text_chunks):
                chunk_records.append({
                    "id": f"{document.id}_{i}",
                    "document_id": document.id,
                    "brain_id": target_brain_id,
                    "chunk_index": i,
                    "content": chunk_txt,
                    "metadata": {
                        "document_id": document.id,
                        "document_title": document.title,
                        "document_type": document.type,
                        "organization_id": document.organization_id or "org_default",
                        "team_id": document.team_id or "",
                        "agent_id": document.agent_id or "",
                        "tags": document.tags
                    }
                })

            # 1. Persist chunks and parent doc into pgvector
            await add_document(
                brain_id=target_brain_id,
                title=document.title,
                content=content[:2000],
                category=document.type,
                author=document.agent_id or "system",
                tags=document.tags
            )
            inserted_chunks = await add_document_chunks(
                brain_id=target_brain_id,
                document_id=document.id,
                chunks=chunk_records
            )

            # 2. Emit Kafka pipeline event for async processing
            await brain_pipeline.emit_chunks_ready(
                brain_id=target_brain_id,
                doc_id=document.id,
                chunks=chunk_records
            )

            logger.info(f"Indexed document {document.id} in Brain [{target_brain_id}] with {inserted_chunks} chunks via pgvector.")
            return True

        except Exception as e:
            logger.error(f"Error indexing document {document.id}: {e}")
            return False

    async def search_relevant_context(
        self,
        query: str,
        organization_id: str = "org_default",
        team_id: str = None,
        agent_id: str = None,
        max_results: int = 5,
        similarity_threshold: float = 0.5,
    ) -> RAGContext:
        """
        Searches across the 4 brain tiers in parallel using pgvector cosine distance,
        traverses the FuzeInfra Neo4j graph for related entities, and assembles context.
        """
        try:
            # Resolve target brains
            hierarchy = await get_agent_brains(
                agent_id=agent_id or "general",
                team_id=team_id,
                organization_id=organization_id
            )
            brain_ids = [b["id"] for b in hierarchy.get("brains", [])]

            hits = await search_multi_brains(
                brain_ids=brain_ids,
                query=query,
                limit=max_results,
                similarity_threshold=similarity_threshold
            )

            relevant_chunks = []
            similarity_scores = []
            seed_entities = set()

            for h in hits:
                cid = h.get("chunk_id") or f"{h.get('document_id')}_0"
                cnt = h.get("content") or ""
                score = float(h.get("score", 0.0))

                chunk = DocumentChunk(
                    id=cid,
                    document_id=h.get("document_id", "unknown"),
                    chunk_index=h.get("chunk_index", 0),
                    content=cnt,
                    metadata=h.get("metadata", {}),
                )
                relevant_chunks.append(chunk)
                similarity_scores.append(score)

                # Collect words as potential entity candidates
                for word in query.split():
                    if len(word) > 4 and word[0].isupper():
                        seed_entities.add(word)

            # GraphRAG 2-hop traversal via FuzeInfra Neo4j
            graph_snippets = []
            if brain_graph.is_available and seed_entities and brain_ids:
                primary_brain = brain_ids[0]
                graph_paths = brain_graph.traverse_2hop_neighborhood(primary_brain, list(seed_entities))
                graph_snippets = [p["path"] for p in graph_paths[:10]]

            # Distilled prompt assembly
            distilled_parts = [f"--- Retrieved Knowledge ({len(relevant_chunks)} sources) ---"]
            for c, s in zip(relevant_chunks, similarity_scores):
                distilled_parts.append(f"[{c.metadata.get('brain_scope', 'KNOWLEDGE')}] {c.content} (score={s:.2f})")
            if graph_snippets:
                distilled_parts.append("\n--- Knowledge Graph Relationships ---")
                distilled_parts.extend(graph_snippets)

            distilled_prompt = "\n".join(distilled_parts)
            context_length = sum(len(c.content) for c in relevant_chunks)

            return RAGContext(
                query=query,
                relevant_chunks=relevant_chunks,
                similarity_scores=similarity_scores,
                total_documents=len(relevant_chunks),
                context_length=context_length,
                graph_context=graph_snippets,
                distilled_prompt=distilled_prompt
            )

        except Exception as e:
            logger.error(f"Error in search_relevant_context: {e}")
            return RAGContext(
                query=query,
                relevant_chunks=[],
                similarity_scores=[],
                total_documents=0,
                context_length=0,
            )

    async def get_context_for_prompt(
        self,
        query: str,
        organization_id: str = "org_default",
        team_id: str = None,
        agent_id: str = None,
        max_tokens: int = 4000,
    ) -> str:
        """Retrieves and formats distilled multi-tier context for agent prompts."""
        rag_ctx = await self.search_relevant_context(
            query=query,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            max_results=8
        )
        return rag_ctx.distilled_prompt or ""

# Global RAG integration instance
rag_integration = RAGIntegration()
