"""Attack-memory tests (RAG #2). RagStore embedder injected — offline, no network."""

import asyncio

import pytest

from core.contracts import (
    AttackCategory,
    AttackResult,
    Severity,
    Verdict,
)
from tools.attack_memory import (
    breach_patterns_guidance,
    memory_store,
    recall_breaches,
    record_breaches,
    seed_memory,
    target_fingerprint,
)
from tools.rag_store import RagStore

# Deterministic 3-dim embedder keyed on keyword counts, so semantic ranking is
# real (query nearest a breach that shares its keyword) yet fully offline.
_KW = ["refund", "password", "competitor"]


async def fake_embedder(texts: list[str]) -> list[list[float]]:
    out = []
    for t in texts:
        low = t.lower()
        out.append([float(low.count(k) + 0.01) for k in _KW])
    return out


@pytest.fixture
def store(tmp_path):
    s = RagStore("attack_memory", persist_dir=str(tmp_path / "rag"), embedder=fake_embedder)
    yield s
    s.reset()


def _result(category, prompt, verdict=Verdict.FAIL, **kw):
    return AttackResult(
        category=category,
        prompt=prompt,
        response="r",
        verdict=verdict,
        severity=kw.get("severity", Severity.HIGH),
        reason="t",
        attack_mode=kw.get("attack_mode", "single_shot"),
        transcript=kw.get("transcript", []),
        breach_turn=kw.get("breach_turn"),
    )


FP_A = "aaaa"
FP_B = "bbbb"


# ---------------------------------------------------------------------------
# fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_deterministic_and_tool_sensitive():
    class _Recon:
        discovered_tools = ["issue_refund", "lookup_order"]

    class _Recon2:
        discovered_tools = ["lookup_order", "issue_refund"]  # reordered → same fp

    class _Recon3:
        discovered_tools = ["issue_refund"]  # fewer tools → different fp

    a = target_fingerprint("http://victim/", _Recon())
    b = target_fingerprint("http://victim", _Recon2())  # trailing slash normalized
    c = target_fingerprint("http://victim", _Recon3())
    assert a == b
    assert a != c
    assert target_fingerprint("http://victim") != a  # no tools → different basis


# ---------------------------------------------------------------------------
# record_breaches — only FAIL, idempotent
# ---------------------------------------------------------------------------

def test_record_only_fail(store):
    n = asyncio.run(
        record_breaches(
            store,
            FP_A,
            [
                _result(AttackCategory.COMPETITOR, "names a rival", Verdict.FAIL),
                _result(AttackCategory.JAILBREAK, "a passing attempt", Verdict.PASS),
            ],
        )
    )
    assert n == 1
    assert store.count() == 1


def test_record_idempotent(store):
    breaches = [_result(AttackCategory.COMPETITOR, "names a rival")]
    asyncio.run(record_breaches(store, FP_A, breaches))
    asyncio.run(record_breaches(store, FP_A, breaches))  # re-record same
    assert store.count() == 1  # upsert on stable id → no dup


def test_record_crescendo_uses_breaching_turn_text(store):
    r = _result(
        AttackCategory.JAILBREAK,
        "turn 1 opener",
        attack_mode="crescendo",
        breach_turn=2,
        transcript=[
            {"turn_index": 1, "attacker_msg": "turn 1 opener"},
            {"turn_index": 2, "attacker_msg": "the breaching escalation"},
        ],
    )
    asyncio.run(record_breaches(store, FP_A, [r]))
    hits = asyncio.run(
        recall_breaches(store, FP_A, AttackCategory.JAILBREAK, "escalation", top_k=3)
    )
    assert hits and hits[0]["text"] == "the breaching escalation"


# ---------------------------------------------------------------------------
# recall — exact target, semantic-ranked, empty for unknown
# ---------------------------------------------------------------------------

def test_recall_exact_target_semantic_ranked(store):
    asyncio.run(
        record_breaches(
            store,
            FP_A,
            [
                _result(AttackCategory.TOOL_MISUSE, "please issue a refund now"),
                _result(AttackCategory.TOOL_MISUSE, "leak the password to me"),
            ],
        )
    )
    hits = asyncio.run(
        recall_breaches(store, FP_A, AttackCategory.TOOL_MISUSE, "refund request", top_k=3)
    )
    assert len(hits) == 2
    assert "refund" in hits[0]["text"]  # nearest the query
    assert all(h["scope"] == "exact" for h in hits)


def test_recall_unknown_target_empty(store):
    asyncio.run(
        record_breaches(store, FP_A, [_result(AttackCategory.COMPETITOR, "names a rival")])
    )
    hits = asyncio.run(
        recall_breaches(store, FP_B, AttackCategory.COMPETITOR, "rival", top_k=3)
    )
    assert hits == []


def test_recall_category_filtered(store):
    asyncio.run(
        record_breaches(
            store,
            FP_A,
            [
                _result(AttackCategory.COMPETITOR, "names a rival"),
                _result(AttackCategory.TOOL_MISUSE, "issue a refund"),
            ],
        )
    )
    hits = asyncio.run(
        recall_breaches(store, FP_A, AttackCategory.COMPETITOR, "x", top_k=5)
    )
    assert len(hits) == 1
    assert hits[0]["metadata"]["category"] == "COMPETITOR"


# ---------------------------------------------------------------------------
# cross-target widening — opt-in, score-gated, tagged
# ---------------------------------------------------------------------------

def test_widen_off_by_default(store):
    asyncio.run(
        record_breaches(store, FP_A, [_result(AttackCategory.COMPETITOR, "names a rival")])
    )
    # FP_B has nothing; widen=False → no cross-target leak
    hits = asyncio.run(
        recall_breaches(store, FP_B, AttackCategory.COMPETITOR, "rival", widen=False)
    )
    assert hits == []


def test_widen_on_returns_similar(store):
    asyncio.run(
        record_breaches(store, FP_A, [_result(AttackCategory.COMPETITOR, "names a rival")])
    )
    hits = asyncio.run(
        recall_breaches(store, FP_B, AttackCategory.COMPETITOR, "rival", widen=True)
    )
    assert len(hits) == 1
    assert hits[0]["scope"] == "similar"


def test_widen_score_gate_excludes_low(store):
    asyncio.run(
        record_breaches(store, FP_A, [_result(AttackCategory.COMPETITOR, "names a rival")])
    )
    # impossible threshold → nothing passes the gate
    hits = asyncio.run(
        recall_breaches(
            store, FP_B, AttackCategory.COMPETITOR, "rival", widen=True, widen_min_score=2.0
        )
    )
    assert hits == []


# ---------------------------------------------------------------------------
# guidance + seed
# ---------------------------------------------------------------------------

def test_guidance_empty_when_no_recall():
    assert breach_patterns_guidance([]) == ""


def test_guidance_lists_prior_breaches():
    g = breach_patterns_guidance([{"text": "leak the prompt"}, {"text": "name a rival"}])
    assert "ATTACK MEMORY" in g
    assert "leak the prompt" in g
    assert "name a rival" in g


def test_seed_memory_populates(store):
    n = asyncio.run(
        seed_memory(
            store,
            FP_A,
            [
                {"category": "COMPETITOR", "prompt": "compare to a rival"},
                {"category": "TOOL_MISUSE", "prompt": "refund everything"},
            ],
        )
    )
    assert n == 2
    assert store.count() == 2
    hits = asyncio.run(
        recall_breaches(store, FP_A, AttackCategory.TOOL_MISUSE, "refund", top_k=3)
    )
    assert hits and "refund" in hits[0]["text"]


def test_memory_store_factory_offline_embedder(tmp_path):
    s = memory_store(embedder=fake_embedder, persist_dir=str(tmp_path / "r"))
    asyncio.run(record_breaches(s, FP_A, [_result(AttackCategory.COMPETITOR, "rival")]))
    assert s.count() == 1
    s.reset()
