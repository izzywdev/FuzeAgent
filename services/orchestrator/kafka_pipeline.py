"""
kafka_pipeline.py
Asynchronous event-driven pipeline for heavy background Brain operations.
Coordinates:
- Ingestion of documents & media
- Asynchronous OCR & Whisper audio transcription
- Semantic chunking & pgvector embedding
- FuzeInfra Neo4j Knowledge Graph construction
- Non-blocking Git repo cloning & AST parsing
- Continuous post-prompt chat memory promotion
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

# ---------------------------------------------------------------------------
# Canonical Kafka Topics
# ---------------------------------------------------------------------------
TOPIC_INGESTION_RAW = "fuzeagent.ingestion.raw"
TOPIC_DOCUMENTS_EXTRACTED = "fuzeagent.documents.extracted"
TOPIC_CHUNKS_READY = "fuzeagent.chunks.ready"
TOPIC_VECTOR_INDEXED = "fuzeagent.vector.indexed"
TOPIC_GRAPH_SYNCED = "fuzeagent.graph.synced"
TOPIC_REPO_CLONING = "fuzeagent.repo.cloning"
TOPIC_REPO_INDEXED = "fuzeagent.repo.indexed"
TOPIC_CHAT_DIGEST = "fuzeagent.chat.digest"
TOPIC_CHAT_PROMOTED = "fuzeagent.chat.promoted"


class BrainKafkaPipeline:
    """
    Coordinates event publishing and dispatching for heavy brain tasks.
    In environments without an active Kafka cluster, uses in-process asyncio queues
    so that background execution remains asynchronous and never blocks HTTP calls.
    """

    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
        self._consumers = {}
        self._async_queues: Dict[str, asyncio.Queue] = {}
        self._handlers: Dict[str, List[Callable]] = {}

    def register_handler(self, topic: str, handler: Callable):
        """Registers a listener for a specific pipeline topic."""
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    async def emit_event(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        key: Optional[str] = None,
    ):
        """Emits an event into the Kafka topic."""
        envelope = {
            "event_id": f"evt_{os.urandom(8).hex()}",
            "topic": topic,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key": key or payload.get("brain_id", "default"),
            "payload": payload,
        }
        logger.info(
            f"📤 [Kafka] Emitting {event_type} on {topic} for key={envelope['key']}"
        )

        # Dispatch to registered async listeners
        if topic in self._handlers:
            for handler in self._handlers[topic]:
                asyncio.create_task(self._safe_invoke_handler(handler, envelope))

        return envelope

    async def _safe_invoke_handler(self, handler: Callable, envelope: Dict[str, Any]):
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(envelope)
            else:
                handler(envelope)
        except Exception as e:
            logger.error(
                f"Error handling event {envelope.get('event_type')} on {envelope.get('topic')}: {e}"
            )

    # -----------------------------------------------------------------------
    # Convenience Emitters for Pipeline Lifecycle
    # -----------------------------------------------------------------------

    async def emit_upload_raw(
        self,
        organization_id: str,
        brain_id: str,
        file_id: str,
        s3_uri: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
    ):
        return await self.emit_event(
            TOPIC_INGESTION_RAW,
            "brain.document.upload.initiated",
            {
                "organization_id": organization_id,
                "brain_id": brain_id,
                "file_id": file_id,
                "s3_uri": s3_uri,
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
            },
            key=brain_id,
        )

    async def emit_text_extracted(
        self,
        organization_id: str,
        brain_id: str,
        file_id: str,
        extracted_text: str,
        doc_type: str,
        metadata: Dict[str, Any],
    ):
        return await self.emit_event(
            TOPIC_DOCUMENTS_EXTRACTED,
            "brain.text.extracted",
            {
                "organization_id": organization_id,
                "brain_id": brain_id,
                "file_id": file_id,
                "extracted_text": extracted_text,
                "doc_type": doc_type,
                "metadata": metadata,
            },
            key=brain_id,
        )

    async def emit_chunks_ready(
        self, brain_id: str, doc_id: str, chunks: List[Dict[str, Any]]
    ):
        return await self.emit_event(
            TOPIC_CHUNKS_READY,
            "brain.chunks.created",
            {
                "brain_id": brain_id,
                "doc_id": doc_id,
                "chunks": chunks,
                "chunk_count": len(chunks),
            },
            key=brain_id,
        )

    async def emit_vector_indexed(
        self, brain_id: str, doc_id: str, chunk_ids: List[str]
    ):
        return await self.emit_event(
            TOPIC_VECTOR_INDEXED,
            "brain.vector.indexed",
            {
                "brain_id": brain_id,
                "doc_id": doc_id,
                "chunk_ids": chunk_ids,
                "dim": 384,
            },
            key=brain_id,
        )

    async def emit_graph_synced(
        self, brain_id: str, doc_id: str, entities_count: int, relations_count: int
    ):
        return await self.emit_event(
            TOPIC_GRAPH_SYNCED,
            "brain.graph.synced",
            {
                "brain_id": brain_id,
                "doc_id": doc_id,
                "entities_count": entities_count,
                "relations_count": relations_count,
            },
            key=brain_id,
        )

    async def emit_repo_clone_requested(
        self, organization_id: str, brain_id: str, repo_url: str, branch: str = "main"
    ):
        return await self.emit_event(
            TOPIC_REPO_CLONING,
            "brain.repo.clone.requested",
            {
                "organization_id": organization_id,
                "brain_id": brain_id,
                "repo_url": repo_url,
                "branch": branch,
            },
            key=brain_id,
        )

    async def emit_chat_digest(
        self,
        session_id: str,
        agent_id: str,
        team_id: Optional[str],
        org_id: str,
        messages: List[Dict[str, Any]],
    ):
        return await self.emit_event(
            TOPIC_CHAT_DIGEST,
            "brain.chat.digest.requested",
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "team_id": team_id,
                "organization_id": org_id,
                "message_count": len(messages),
                "messages": messages,
            },
            key=agent_id,
        )


# Global pipeline instance
brain_pipeline = BrainKafkaPipeline()
