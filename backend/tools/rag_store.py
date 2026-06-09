"""Generic persistent text+metadata vector store with hybrid retrieval.

Reusable foundation: stores {id, text, metadata} records with Gemini embeddings
in a disk-backed Chroma collection, and retrieves via HYBRID search — a metadata
`where` filter first, then semantic ranking by embedding similarity.

Knows NOTHING about attacks, techniques, OWASP, or campaigns. Attack-specific
schemas live in the slices that USE this (technique catalog, attack memory).
"""

import asyncio

import chromadb
from google import genai

from core.config import EMBED_MODEL, GEMINI_API_KEY, RAG_DIR, USE_VERTEX
from core.retry import with_retry


def _genai_client():
    # Mirror judge.py: Vertex (ADC, no key) vs AI Studio (api_key).
    if USE_VERTEX:
        return genai.Client()
    return genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


async def embed_texts(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    """Embed texts via Gemini on Vertex. Returns one vector per text.

    Empty input → empty list (no API call). Transient errors retried via
    core.retry.with_retry.
    """
    if not texts:
        return []
    client = _genai_client()
    if client is None:
        raise RuntimeError(
            "no genai client: set GOOGLE_GENAI_USE_VERTEXAI=1 (+ADC) or GEMINI_API_KEY"
        )

    def _call():
        return client.models.embed_content(model=model, contents=texts)

    resp = await with_retry(lambda: asyncio.to_thread(_call))
    return [list(e.values) for e in resp.embeddings]


class RagStore:
    """Disk-backed Chroma collection with metadata-filtered hybrid query.

    embedder is injectable (async callable list[str] -> list[vector]) so tests
    run offline. Defaults to the real Vertex embed_texts.
    """

    def __init__(
        self,
        collection_name: str,
        persist_dir: str = RAG_DIR,
        embedder=embed_texts,
    ) -> None:
        self._embedder = embedder
        self._name = collection_name
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._get_or_create()

    def _get_or_create(self):
        return self._client.get_or_create_collection(
            name=self._name, metadata={"hnsw:space": "cosine"}
        )

    async def add(self, records: list[dict]) -> None:
        """Upsert records: each {id, text, metadata: dict}. Idempotent on id."""
        if not records:
            return
        texts = [r["text"] for r in records]
        embeddings = await self._embedder(texts)
        # Chroma rejects empty metadata dicts → send None when absent.
        metadatas = [r.get("metadata") or None for r in records]
        self._collection.upsert(
            ids=[r["id"] for r in records],
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    async def query(
        self, query_text: str, where: dict | None = None, top_k: int = 5
    ) -> list[dict]:
        """Hybrid retrieval: apply `where` filter, then semantic rank.

        Returns [{id, text, metadata, score}], nearest first (score = 1 - cosine
        distance). `where=None` → pure semantic. Empty store → [].
        """
        if self.count() == 0:
            return []
        vec = (await self._embedder([query_text]))[0]
        kwargs = {"query_embeddings": [vec], "n_results": top_k}
        if where:
            kwargs["where"] = where
        res = self._collection.query(**kwargs)
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        return [
            {"id": i, "text": d, "metadata": m or {}, "score": 1.0 - dist}
            for i, d, m, dist in zip(ids, docs, metas, dists)
        ]

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Drop all records (test cleanup / demo re-seeding)."""
        self._client.delete_collection(self._name)
        self._collection = self._get_or_create()
