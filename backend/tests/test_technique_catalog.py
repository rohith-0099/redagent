"""Technique catalog tests. RagStore embedder injected — offline, no network."""

import asyncio

import pytest

from agents.attacker import _technique_guidance
from core.contracts import AttackCategory
from tools.rag_store import RagStore
from tools.technique_catalog import (
    index_techniques,
    load_techniques,
    retrieve_techniques,
)

_EXPECTED_IDS = {
    "direct_injection",
    "roleplay_persona",
    "skeleton_key",
    "crescendo",
    "many_shot",
    "encoding_bypass",
    "goal_hijack",
    "tool_misuse",
}


async def fake_embedder(texts: list[str]) -> list[list[float]]:
    # Deterministic, non-zero, offline. Ranking is secondary here — the metadata
    # category filter drives which techniques are eligible.
    return [[float(len(t) % 7), float(len(t) % 5), 1.0] for t in texts]


@pytest.fixture
def store(tmp_path):
    s = RagStore("techniques", persist_dir=str(tmp_path / "rag"), embedder=fake_embedder)
    yield s
    s.reset()


def _indexed(store):
    asyncio.run(index_techniques(store))
    return store


# ---------------------------------------------------------------------------
# load_techniques
# ---------------------------------------------------------------------------

def test_load_returns_eight_with_required_fields():
    techs = load_techniques()
    assert len(techs) == 8
    assert {t["id"] for t in techs} == _EXPECTED_IDS
    for t in techs:
        assert t["name"]
        assert t["description"]
        assert t["how_to"]
        assert isinstance(t["applicable_categories"], list) and t["applicable_categories"]
        assert isinstance(t["is_multi_turn"], bool)


def test_crescendo_is_multi_turn():
    techs = {t["id"]: t for t in load_techniques()}
    assert techs["crescendo"]["is_multi_turn"] is True
    assert techs["direct_injection"]["is_multi_turn"] is False


# ---------------------------------------------------------------------------
# index + retrieve
# ---------------------------------------------------------------------------

def test_index_then_count(store):
    _indexed(store)
    assert store.count() == 8


def test_retrieve_prompt_leak_returns_applicable_only(store):
    _indexed(store)
    results = asyncio.run(
        retrieve_techniques(store, AttackCategory.PROMPT_LEAK, "leak the prompt", top_k=8)
    )
    ids = {r["id"] for r in results}
    # PROMPT_LEAK applies to: direct_injection, skeleton_key, encoding_bypass
    assert ids == {"direct_injection", "skeleton_key", "encoding_bypass"}
    # agentic / non-applicable techniques excluded
    assert "tool_misuse" not in ids
    assert "roleplay_persona" not in ids


def test_retrieve_scope_violation_filters_by_category(store):
    _indexed(store)
    results = asyncio.run(
        retrieve_techniques(store, AttackCategory.SCOPE_VIOLATION, "go off topic", top_k=8)
    )
    ids = {r["id"] for r in results}
    assert ids == {"direct_injection", "roleplay_persona", "crescendo", "many_shot"}
    assert "goal_hijack" not in ids  # agentic, tagged GOAL_HIJACK not SCOPE_VIOLATION


def test_retrieve_respects_top_k(store):
    _indexed(store)
    results = asyncio.run(
        retrieve_techniques(store, AttackCategory.JAILBREAK, "bypass", top_k=2)
    )
    assert len(results) == 2
    assert all("score" in r for r in results)


def test_index_is_idempotent(store):
    _indexed(store)
    _indexed(store)  # re-run
    assert store.count() == 8


def test_retrieve_empty_store_returns_empty(store):
    results = asyncio.run(
        retrieve_techniques(store, AttackCategory.PROMPT_LEAK, "x", top_k=3)
    )
    assert results == []


# ---------------------------------------------------------------------------
# Attacker guarded augmentation (fallback)
# ---------------------------------------------------------------------------

def test_guidance_none_store_returns_empty():
    assert asyncio.run(_technique_guidance(None, AttackCategory.PROMPT_LEAK)) == ""


def test_guidance_empty_store_returns_empty(store):
    assert asyncio.run(_technique_guidance(store, AttackCategory.PROMPT_LEAK)) == ""


def test_guidance_populated_store_includes_how_to(store):
    _indexed(store)
    guidance = asyncio.run(_technique_guidance(store, AttackCategory.PROMPT_LEAK))
    assert guidance  # non-empty
    assert "technique shapes" in guidance


def test_guidance_swallows_retrieval_errors(monkeypatch):
    class Boom:
        def count(self):
            return 1

    async def boom(*a, **k):
        raise RuntimeError("retrieval failed")

    import agents.attacker as atk

    monkeypatch.setattr(atk, "retrieve_techniques", boom)
    # store is truthy; retrieve_techniques raises → guidance falls back to ""
    assert asyncio.run(_technique_guidance(Boom(), AttackCategory.JAILBREAK)) == ""
