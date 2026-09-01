"""
Knowledge Management System for FuzeAgent
Handles document upload, storage, processing, and RAG integration
"""

import asyncio
import ipaddress
import logging
import mimetypes
import os
import re
import socket
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import markdown

# Document processing imports
import pypdf
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


# ---------------------------------------------------------------------------
# Input validation for anything that reaches the filesystem or the network.
#
# Every public method here takes caller-supplied `organization_id` / `team_id` /
# `agent_id` / `doc_id` / `filename`, and those used to be interpolated straight
# into a path (CodeQL py/path-injection, CWE-22), and `url` straight into an
# outbound request (py/full-ssrf, CWE-918).
#
# The approach is REJECT, never sanitise. A sanitiser has to be exhaustive to be
# correct ("..", "....//", URL-encoding, NUL, absolute paths, Windows drive
# letters, unicode normalisation); an allowlist has to be right once. Where the
# value does not need to be caller-controlled at all -- the on-disk filename --
# we simply stop using the caller's value, which removes the class instead of
# filtering it.
# ---------------------------------------------------------------------------

# Deliberately strict: no dots, so ".." can never be expressed regardless of any
# encoding trick, and no separators.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_MAX_REDIRECTS = 5


class UnsafeInputError(ValueError):
    """A caller-supplied value was rejected before reaching the disk/network."""


def _validate_scope_id(value: Optional[str], kind: str) -> Optional[str]:
    """Allow a scope id through only if it matches the strict allowlist."""
    if value is None:
        return None
    if not isinstance(value, str) or not _SAFE_ID_RE.fullmatch(value):
        raise UnsafeInputError(f"Invalid {kind}: must match {_SAFE_ID_RE.pattern}")
    return value


def _validate_doc_id(doc_id: str) -> str:
    """Document ids are server-minted uuid4. Anything else is not one of ours.

    This matters on the read/update/delete paths, where `doc_id` comes back from
    the client and is used to build a filename and, in delete_document(), a glob
    pattern that feeds unlink().
    """
    try:
        return str(uuid.UUID(str(doc_id)))
    except (AttributeError, TypeError, ValueError) as exc:
        raise UnsafeInputError("Invalid document id: expected a UUID") from exc


def _ensure_within(base: Path, candidate: Path) -> Path:
    """Assert `candidate` resolves inside `base`; return the resolved path.

    Defence in depth, applied even when the components were already validated: a
    filter you believe is complete and a containment check you can prove are not
    the same thing. Resolving both sides also collapses symlinks, so a symlinked
    entry inside the storage root cannot be used to escape it either.
    """
    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved != base_resolved and not candidate_resolved.is_relative_to(
        base_resolved
    ):
        raise UnsafeInputError(
            f"Refusing to operate on a path outside the storage root: "
            f"{candidate_resolved}"
        )
    return candidate_resolved


def _validate_public_url(url: str) -> str:
    """Reject non-HTTP(S) schemes and any host resolving to a non-public address.

    Without this, upload_url() is a full SSRF primitive: running in-cluster it
    reaches every internal Service, and -- worst -- the cloud instance metadata
    endpoint at 169.254.169.254, which hands out credentials to anyone who can
    make the server issue a GET.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeInputError(
            f"Unsupported URL scheme {parsed.scheme!r}: only http/https are allowed"
        )
    host = parsed.hostname
    if not host:
        raise UnsafeInputError("URL has no host")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeInputError(f"Could not resolve host {host!r}") from exc

    for info in addrinfo:
        ip = ipaddress.ip_address(info[4][0])
        # is_private already covers 10/8, 172.16/12, 192.168/16 and fc00::/7;
        # the rest are spelled out because they are the ones that actually get
        # abused (169.254.169.254 is link-local, ::1/127.0.0.1 loopback).
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeInputError(
                f"Refusing to fetch {host!r}: resolves to non-public address {ip}"
            )
    return url


def _fetch_url_safely(url: str, timeout: int = 30):
    """GET `url`, re-validating the target on every redirect hop.

    Redirects are followed manually because `requests` would otherwise follow a
    302 to http://169.254.169.254/ *after* our check had already passed on the
    original URL -- validating only the first URL is not a control at all.

    KNOWN LIMITATION, stated rather than implied away: this is still susceptible
    to DNS rebinding. The hostname is resolved here for validation and resolved
    again by the OS when the socket is opened, so a hostile resolver can answer
    with a public address the first time and a private one the second. Closing
    that requires pinning the validated IP for the actual connection (a custom
    requests transport adapter / connection-level check), which is a larger
    change than this fix.
    """
    current = url
    for _ in range(_MAX_REDIRECTS):
        _validate_public_url(current)
        response = requests.get(current, timeout=timeout, allow_redirects=False)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if not location:
                return response
            current = urljoin(current, location)
            continue
        return response
    raise UnsafeInputError(f"Too many redirects while fetching {url!r}")


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
        """Get the appropriate storage path based on scope.

        Every caller of this method passes ids straight from the request, so the
        validation lives here -- one chokepoint that all of get/upload/delete
        funnel through -- rather than being repeated (and eventually forgotten)
        at each call site.
        """
        agent_id = _validate_scope_id(agent_id, "agent_id")
        team_id = _validate_scope_id(team_id, "team_id")
        organization_id = _validate_scope_id(organization_id, "organization_id")

        if agent_id:
            candidate = self.storage_path / "agents" / agent_id
        elif team_id:
            candidate = self.storage_path / "teams" / team_id
        elif organization_id:
            candidate = self.storage_path / "organizations" / organization_id
        else:
            candidate = self.storage_path / "temp"

        return _ensure_within(self.storage_path, candidate)

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
                reader = pypdf.PdfReader(file)
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

        # Save file.
        #
        # The on-disk name is the SERVER-MINTED doc_id plus the extension we just
        # validated against SUPPORTED_TYPES. The caller's `filename` is never used
        # to build a path -- it is preserved in the metadata below, where it is
        # inert data. This is what actually removes the traversal here: there is
        # no longer any caller-controlled component in the path to escape with.
        file_path = _ensure_within(
            storage_path, storage_path / f"{doc_id}{file_extension}"
        )

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
                content_preview=(
                    extracted_text[:500] + "..."
                    if len(extracted_text) > 500
                    else extracted_text
                ),
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
            # Fetch URL content through the SSRF guard (scheme allowlist,
            # non-public address rejection, re-validated on every redirect hop).
            response = _fetch_url_safely(url, timeout=30)
            response.raise_for_status()

            # Extract text content
            soup = BeautifulSoup(response.content, "html.parser")
            extracted_text = soup.get_text(strip=True)
            word_count = len(extracted_text.split())

            # Create metadata
            metadata = DocumentMetadata(
                id=doc_id,
                title=(
                    title or soup.find("title").get_text()
                    if soup.find("title")
                    else url
                ),
                filename=f"url_{doc_id}.html",
                type="link",
                mime_type="text/html",
                size=len(response.content),
                status="active",
                upload_date=datetime.now(),
                last_modified=datetime.now(),
                content_preview=(
                    extracted_text[:500] + "..."
                    if len(extracted_text) > 500
                    else extracted_text
                ),
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
            file_path = _ensure_within(
                storage_path, storage_path / f"{doc_id}_url_content.html"
            )

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

        doc_id = _validate_doc_id(doc_id)
        storage_path = self._get_storage_path(organization_id, team_id, agent_id)
        metadata_file = _ensure_within(
            storage_path, storage_path / f"{doc_id}.metadata.json"
        )

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
            # Validated first: an unvalidated doc_id here becomes a glob pattern
            # that feeds unlink(), so a traversing or wildcard value would delete
            # files outside this scope -- or outside the storage root entirely.
            doc_id = _validate_doc_id(doc_id)
            storage_path = self._get_storage_path(organization_id, team_id, agent_id)

            # Remove from RAG index first
            try:
                from rag_integration import rag_system

                await rag_system.remove_document_from_index(doc_id)
                logger.info(f"Document removed from RAG index: {doc_id}")
            except Exception as e:
                logger.error(f"Error removing document from RAG index: {e}")

            # Find and delete files. doc_id is a validated UUID by now, so the
            # pattern cannot traverse; the containment check is belt-and-braces
            # for anything glob() might surface via a symlinked entry.
            for file_path in storage_path.glob(f"{doc_id}*"):
                _ensure_within(storage_path, file_path)
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
        metadata_file = _ensure_within(
            storage_path,
            storage_path / f"{_validate_doc_id(metadata.id)}.metadata.json",
        )

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
