from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import chromadb
from backend.app.rag.models import KBChunk, SearchResultItem
from backend.app.rag.vector_store.base import BaseVectorStore
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """Persistent ChromaDB vector store implementation for Knowledge Base retrieval."""

    COLLECTION_NAME = "service_desk_kb"
    DEFAULT_COLLECTION_NAME = COLLECTION_NAME

    def __init__(
        self,
        persist_dir: str | Path = "./data/chroma_db",
        model_name: str = "BAAI/bge-m3",
        dimension: int = 1024,
        collection_name: Optional[str] = None,
        client: Optional[ClientAPI] = None,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._persist_dir = str(persist_dir)
        self._collection_name = collection_name or self.DEFAULT_COLLECTION_NAME

        if client is not None:
            self._client = client
        elif self._persist_dir == ":memory:":
            self._client = chromadb.EphemeralClient()
        else:
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        self._collection = self._get_or_create_collection()


    def _get_or_create_collection(self) -> Any:
        metadata = {
            "hnsw:space": "cosine",
            "embedding_model": self._model_name,
            "embedding_dim": self._dimension,
        }
        try:
            coll = self._client.get_collection(name=self._collection_name)
            coll_meta = coll.metadata or {}
            existing_model = coll_meta.get("embedding_model")
            if existing_model and existing_model != self._model_name:
                logger.warning(
                    "ChromaDB collection was created with model '%s' but current model is '%s'",
                    existing_model,
                    self._model_name,
                )
            return coll
        except Exception:
            return self._client.create_collection(
                name=self._collection_name,
                metadata=metadata,
            )


    def add_chunks(self, chunks: List[KBChunk], embeddings: List[List[float]]) -> None:
        if not chunks:
            return

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.text)
            # Ensure all metadata values are primitive types
            meta = {
                "doc_id": str(chunk.doc_id),
                "doc_title": str(chunk.doc_title),
                "category": str(chunk.category),
                "heading": str(chunk.heading),
                "chunk_index": int(chunk.chunk_index),
                "source_path": str(chunk.source_path),
                "tags": str(chunk.metadata.get("tags", "")),
                "version": str(chunk.metadata.get("version", "")),
            }
            metadatas.append(meta)

        # Batch upsert into Chroma
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def delete_document_chunks(self, doc_ids: List[str]) -> int:
        if not doc_ids:
            return 0
        deleted_count = 0
        for doc_id in doc_ids:
            try:
                # Find chunks for this doc_id
                existing = self._collection.get(where={"doc_id": doc_id})
                ids_to_delete = existing.get("ids", [])
                if ids_to_delete:
                    self._collection.delete(ids=ids_to_delete)
                    deleted_count += len(ids_to_delete)
            except Exception as e:
                logger.warning("Error deleting chunks for doc_id '%s': %s", doc_id, e)
        return deleted_count

    def query_similar(self, query_embedding: List[float], top_k: int = 5) -> List[SearchResultItem]:
        total_chunks = self.count_chunks()
        if total_chunks == 0:
            return []

        actual_k = min(top_k, total_chunks)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            include=["documents", "metadatas", "distances"],
        )

        items: List[SearchResultItem] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids):
            doc_text = docs[i] if i < len(docs) else ""
            meta = metas[i] if i < len(metas) else {}
            dist = distances[i] if i < len(distances) else 1.0
            # Cosine distance in Chroma: score = 1.0 - distance
            score = round(max(0.0, 1.0 - float(dist)), 4)

            items.append(
                SearchResultItem(
                    chunk_id=chunk_id,
                    doc_id=str(meta.get("doc_id", "")),
                    doc_title=str(meta.get("doc_title", "")),
                    category=str(meta.get("category", "")),
                    heading=str(meta.get("heading", "")),
                    text=doc_text,
                    score=score,
                    source_path=str(meta.get("source_path", "")),
                    metadata=meta,
                )
            )

        return items

    def count_chunks(self) -> int:
        return self._collection.count()

    def get_indexed_doc_ids(self) -> Set[str]:
        count = self.count_chunks()
        if count == 0:
            return set()
        # Retrieve all metadatas to extract doc_ids
        records = self._collection.get(include=["metadatas"])
        doc_ids: Set[str] = set()
        for meta in records.get("metadatas", []):
            if meta and "doc_id" in meta:
                doc_ids.add(str(meta["doc_id"]))
        return doc_ids

    def get_collection_metadata(self) -> Dict[str, Any]:
        coll_meta = self._collection.metadata or {}
        return {
            "collection_name": self._collection_name,
            "persist_dir": self._persist_dir,
            "total_chunks": self.count_chunks(),
            "model_name": coll_meta.get("embedding_model", self._model_name),
            "dimension": coll_meta.get("embedding_dim", self._dimension),
        }

    def reset(self) -> None:
        try:
            self._client.delete_collection(name=self._collection_name)
        except Exception:
            pass
        self._collection = self._get_or_create_collection()

