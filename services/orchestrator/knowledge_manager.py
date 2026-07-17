"""
Knowledge Management System for FuzeAgent
Handles document upload, storage, processing, and RAG integration
"""
import asyncio
import logging
import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional
from urllib.parse import urlparse

import markdown

# Document processing imports
import PyPDF2
import requests
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Storage configuration
KNOWLEDGE_STORAGE_PATH = os.environ.get(
    "KNOWLEDGE_STORAGE_PATH", "/app/knowledge_storage"
)
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "50000000"))  # 50MB default
SUPPORTED_TYPES = [".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".json"]


class DocumentMetadata(BaseModel):
    """Document metadata model"""

    id: str
    title: str
    filename: str
    type: str  # 'document', 'link', 'text'
    mime_type: Optional[str] = None
    size: Optional[int] = None
    status: str = "processing"  # 'processing', 'active', 'error'
    upload_date: datetime
    last_modified: datetime
    content_preview: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    word_count: Optional[int] = None
    extracted_text: Optional[str] = None
    vector_embedding_id: Optional[str] = None


class KnowledgeManager:
    """Main knowledge management class"""

    def __init__(self):
        """Initialize the knowledge manager"""
        self.storage_path = Path(KNOWLEDGE_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.storage_path / "organizations").mkdir(exist_ok=True)
        (self.storage_path / "teams").mkdir(exist_ok=True)
        (self.storage_path / "agents").mkdir(exist_ok=True)
        (self.storage_path / "temp").mkdir(exist_ok=True)

        logger.info(
            f"Knowledge Manager initialized with storage path: {self.storage_path}"
        )

    def _get_storage_path(
        self, organization_id: str = None, team_id: str = None, agent_id: str = None
    ) -> Path:
        """Get the appropriate storage path based on scope"""
        if agent_id:
            return self.storage_path / "agents" / agent_id
        elif team_id:
            return self.storage_path / "teams" / team_id
        elif organization_id:
            return self.storage_path / "organizations" / organization_id
        else:
            return self.storage_path / "temp"

    def _extract_text_from_file(self, file_path: Path) -> tuple[str, int]:
        """Extract text content from various file types"""
        try:
            suffix = file_path.suffix.lower()
            text = ""

            if suffix == ".pdf":
                text = self._extract_from_pdf(file_path)
            elif suffix in [".docx"]:
                text = self._extract_from_docx(file_path)
            elif suffix in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif suffix == ".html":
                text = self._extract_from_html(file_path)
            elif suffix == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    import json

                    data = json.load(f)
                    text = json.dumps(data, indent=2)
            else:
                # Try to read as plain text
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except:
                    text = f"Unable to extract text from {suffix} file"

            word_count = len(text.split()) if text else 0
            return text, word_count

        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return f"Error extracting text: {str(e)}", 0

    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting from PDF {file_path}: {e}")
            text = f"Error reading PDF: {str(e)}"
        return text

    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error extracting from DOCX {file_path}: {e}")
            return f"Error reading DOCX: {str(e)}"

    def _extract_from_html(self, file_path: Path) -> str:
        """Extract text from HTML file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
                return soup.get_text(strip=True)
        except Exception as e:
            logger.error(f"Error extracting from HTML {file_path}: {e}")
            return f"Error reading HTML: {str(e)}"

    async def upload_document(
        self,
        file_content: BinaryIO,
        filename: str,
        title: str = None,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
        tags: List[str] = None,
    ) -> DocumentMetadata:
        """Upload and process a document"""

        # Generate unique document ID
        doc_id = str(uuid.uuid4())

        # Determine file type and validate
        file_extension = Path(filename).suffix.lower()
        if file_extension not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Get storage path
        storage_path = self._get_storage_path(organization_id, team_id, agent_id)
        storage_path.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = storage_path / f"{doc_id}_{filename}"

        try:
            # Read and save file content
            content = file_content.read()
            if len(content) > MAX_FILE_SIZE:
                raise ValueError(
                    f"File size exceeds maximum allowed size of {MAX_FILE_SIZE} bytes"
                )

            with open(file_path, "wb") as f:
                f.write(content)

            # Extract text content
            extracted_text, word_count = self._extract_text_from_file(file_path)

            # Create metadata
            metadata = DocumentMetadata(
                id=doc_id,
                title=title or filename,
                filename=filename,
                type="document",
                mime_type=mimetypes.guess_type(filename)[0],
                size=len(content),
                status="active",
                upload_date=datetime.now(),
                last_modified=datetime.now(),
                content_preview=extracted_text[:500] + "..."
                if len(extracted_text) > 500
                else extracted_text,
                tags=tags or [],
                organization_id=organization_id,
                team_id=team_id,
                agent_id=agent_id,
                word_count=word_count,
                extracted_text=extracted_text,
            )

            # Save metadata
            await self._save_metadata(metadata)

            # Generate vector embeddings for RAG
            try:
                from rag_integration import rag_system

                success = await rag_system.index_document(metadata)
                if success:
                    logger.info(f"Document indexed for RAG: {doc_id}")
                else:
                    logger.warning(f"Failed to index document for RAG: {doc_id}")
            except Exception as e:
                logger.error(f"Error indexing document for RAG: {e}")

            # Send WebSocket notification about knowledge update
            try:
                from websocket_manager import notify_knowledge_update

                await notify_knowledge_update(
                    organization_id=organization_id,
                    team_id=team_id,
                    agent_id=agent_id,
                    document_title=title or filename,
                )
            except Exception as e:
                logger.error(f"Error sending knowledge update notification: {e}")

            logger.info(f"Document uploaded successfully: {doc_id} ({filename})")
            return metadata

        except Exception as e:
            # Clean up file if error occurred
            if file_path.exists():
                file_path.unlink()
            logger.error(f"Error uploading document {filename}: {e}")
            raise

    async def upload_url(
        self,
        url: str,
        title: str = None,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
        tags: List[str] = None,
    ) -> DocumentMetadata:
        """Upload content from a URL"""

        doc_id = str(uuid.uuid4())

        try:
            # Fetch URL content
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Extract text content
            soup = BeautifulSoup(response.content, "html.parser")
            extracted_text = soup.get_text(strip=True)
            word_count = len(extracted_text.split())

            # Create metadata
            metadata = DocumentMetadata(
                id=doc_id,
                title=title or soup.find("title").get_text()
                if soup.find("title")
                else url,
                filename=f"url_{doc_id}.html",
                type="link",
                mime_type="text/html",
                size=len(response.content),
                status="active",
                upload_date=datetime.now(),
                last_modified=datetime.now(),
                content_preview=extracted_text[:500] + "..."
                if len(extracted_text) > 500
                else extracted_text,
                tags=tags or [],
                source_url=url,
                organization_id=organization_id,
                team_id=team_id,
                agent_id=agent_id,
                word_count=word_count,
                extracted_text=extracted_text,
            )

            # Save content to file
            storage_path = self._get_storage_path(organization_id, team_id, agent_id)
            storage_path.mkdir(parents=True, exist_ok=True)
            file_path = storage_path / f"{doc_id}_url_content.html"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            # Save metadata
            await self._save_metadata(metadata)

            # Generate vector embeddings for RAG
            try:
                from rag_integration import rag_system

                success = await rag_system.index_document(metadata)
                if success:
                    logger.info(f"URL document indexed for RAG: {doc_id}")
                else:
                    logger.warning(f"Failed to index URL document for RAG: {doc_id}")
            except Exception as e:
                logger.error(f"Error indexing URL document for RAG: {e}")

            logger.info(f"URL content uploaded successfully: {doc_id} ({url})")
            return metadata

        except Exception as e:
            logger.error(f"Error uploading URL {url}: {e}")
            raise

    async def get_documents(
        self, organization_id: str = None, team_id: str = None, agent_id: str = None
    ) -> List[DocumentMetadata]:
        """Get list of documents for a scope"""

        storage_path = self._get_storage_path(organization_id, team_id, agent_id)
        documents = []

        if not storage_path.exists():
            return documents

        try:
            for metadata_file in storage_path.glob("*.metadata.json"):
                metadata = await self._load_metadata(metadata_file)
                if metadata:
                    documents.append(metadata)

            # Sort by upload date (newest first)
            documents.sort(key=lambda x: x.upload_date, reverse=True)
            return documents

        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

    async def get_document_content(
        self,
        doc_id: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
    ) -> Optional[str]:
        """Get full content of a document"""

        try:
            metadata = await self.get_document_metadata(
                doc_id, organization_id, team_id, agent_id
            )
            if not metadata:
                return None

            return metadata.extracted_text

        except Exception as e:
            logger.error(f"Error getting document content {doc_id}: {e}")
            return None

    async def get_document_metadata(
        self,
        doc_id: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
    ) -> Optional[DocumentMetadata]:
        """Get document metadata"""

        storage_path = self._get_storage_path(organization_id, team_id, agent_id)
        metadata_file = storage_path / f"{doc_id}.metadata.json"

        if not metadata_file.exists():
            return None

        return await self._load_metadata(metadata_file)

    async def update_document(
        self,
        doc_id: str,
        title: str = None,
        tags: List[str] = None,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
    ) -> Optional[DocumentMetadata]:
        """Update document metadata"""

        metadata = await self.get_document_metadata(
            doc_id, organization_id, team_id, agent_id
        )
        if not metadata:
            return None

        if title:
            metadata.title = title
        if tags is not None:
            metadata.tags = tags

        metadata.last_modified = datetime.now()

        await self._save_metadata(metadata)
        return metadata

    async def delete_document(
        self,
        doc_id: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
    ) -> bool:
        """Delete a document"""

        try:
            storage_path = self._get_storage_path(organization_id, team_id, agent_id)

            # Remove from RAG index first
            try:
                from rag_integration import rag_system

                await rag_system.remove_document_from_index(doc_id)
                logger.info(f"Document removed from RAG index: {doc_id}")
            except Exception as e:
                logger.error(f"Error removing document from RAG index: {e}")

            # Find and delete files
            for file_path in storage_path.glob(f"{doc_id}*"):
                file_path.unlink()

            logger.info(f"Document deleted: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    async def search_documents(
        self,
        query: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
        limit: int = 10,
    ) -> List[DocumentMetadata]:
        """Search documents by content (simple text search for now)"""

        documents = await self.get_documents(organization_id, team_id, agent_id)
        results = []

        query_lower = query.lower()

        for doc in documents:
            # Search in title, content preview, and tags
            if (
                query_lower in doc.title.lower()
                or (doc.content_preview and query_lower in doc.content_preview.lower())
                or any(query_lower in tag.lower() for tag in doc.tags)
            ):
                results.append(doc)

                if len(results) >= limit:
                    break

        return results

    async def _save_metadata(self, metadata: DocumentMetadata):
        """Save document metadata to file"""

        storage_path = self._get_storage_path(
            metadata.organization_id, metadata.team_id, metadata.agent_id
        )
        metadata_file = storage_path / f"{metadata.id}.metadata.json"

        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

    async def _load_metadata(self, metadata_file: Path) -> Optional[DocumentMetadata]:
        """Load document metadata from file"""

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = f.read()
                return DocumentMetadata.model_validate_json(data)
        except Exception as e:
            logger.error(f"Error loading metadata from {metadata_file}: {e}")
            return None


# Global knowledge manager instance
knowledge_manager = KnowledgeManager()
