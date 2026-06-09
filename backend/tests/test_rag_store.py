"""RagStore tests. Embedder mocked (injected) — no real network, offline."""

import asyncio

import pytest

from tools.rag_store import RagStore

# Tiny deterministic 3-dim embedder keyed on substring, so similarity is
# predictable without any network. Each text maps to a one-hot-ish vector.
_VECTORS = {
    "apple": [1.0, 0.0, 0.0],
    "banana": [0.0, 1.0, 0.0],
    "carrot": [0.0, 0.0, 1.0],
}


async def fake_embedder(texts: list[str]) -> list[list[float]]:
    out = []
    for t in texts:
        vec = [0.0, 0.0, 0.0]
        for i, key in enumerate(_VECTORS):
            if key in t.lower():
                vec = _VECTORS[key]
                break
        out.append(vec)
    return out


@pytest.fixture
def store(tmp_path):
    s = RagStore(
        collection_name="testcol",
        persist_dir=str(tmp_path / "rag"),
        embedder=fake_embedder,
    )
    yield s
    s.reset()


def _add(store, records):
    asyncio.run(store.add(records))


def _query(store, text, where=None, top_k=5):
    return asyncio.run(store.query(text, where=where, top_k=top_k))


def test_add_then_query_returns_ranked(store):
    _add(
        store,
        [
            {"id": "1", "text": "fresh apple", "metadata": {"kind": "fruit"}},
            {"id": "2", "text": "ripe banana", "metadata": {"kind": "fruit"}},
            {"id": "3", "text": "orange carrot", "metadata": {"kind": "veg"}},
        ],
    )
    results = _query(store, "apple please")
    assert results[0]["id"] == "1"  # nearest match ranked first
    assert results[0]["text"] == "fresh apple"
    assert results[0]["metadata"] == {"kind": "fruit"}
    assert results[0]["score"] == pytest.approx(1.0)  # identical vector


def test_where_filter_restricts_results(store):
    _add(
        store,
        [
            {"id": "1", "text": "fresh apple", "metadata": {"kind": "fruit"}},
            {"id": "2", "text": "orange carrot", "metadata": {"kind": "veg"}},
        ],
    )
    results = _query(store, "carrot", where={"kind": "veg"})
    assert [r["id"] for r in results] == ["2"]
    assert all(r["metadata"]["kind"] == "veg" for r in results)


def test_query_no_match_returns_empty_filter(store):
    _add(store, [{"id": "1", "text": "fresh apple", "metadata": {"kind": "fruit"}}])
    assert _query(store, "apple", where={"kind": "nonexistent"}) == []


def test_query_empty_store_returns_empty(store):
    assert _query(store, "anything") == []


def test_upsert_is_idempotent_on_id(store):
    _add(store, [{"id": "1", "text": "fresh apple", "metadata": {"kind": "fruit"}}])
    _add(store, [{"id": "1", "text": "ripe banana", "metadata": {"kind": "fruit"}}])
    assert store.count() == 1
    results = _query(store, "banana")
    assert results[0]["text"] == "ripe banana"  # updated, not duplicated


def test_count_and_reset(store):
    _add(
        store,
        [
            {"id": "1", "text": "fresh apple", "metadata": {"kind": "fruit"}},
            {"id": "2", "text": "ripe banana", "metadata": {"kind": "fruit"}},
        ],
    )
    assert store.count() == 2
    store.reset()
    assert store.count() == 0


def test_add_empty_records_noop(store):
    _add(store, [])
    assert store.count() == 0


def test_record_without_metadata(store):
    _add(store, [{"id": "1", "text": "fresh apple"}])
    results = _query(store, "apple")
    assert results[0]["id"] == "1"
    assert results[0]["metadata"] == {}


def test_embed_texts_empty_input_no_call():
    from tools.rag_store import embed_texts

    assert asyncio.run(embed_texts([])) == []
