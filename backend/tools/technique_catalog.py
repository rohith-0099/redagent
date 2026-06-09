"""Technique catalog — RAG use #1.

Curated library of red-team technique SHAPES (defensive, app-policy focused per
CLAUDE.md §8). Loads them as data, indexes them into the SHARED RagStore, and
retrieves category-appropriate techniques (metadata filter + semantic rank) so
the Attacker can generate technique-informed, target-specific attacks.

Chroma metadata is scalar-only, so a technique's multiple applicable_categories
are stored as per-category boolean flags ("cat_<CATEGORY>": True).
"""

import json
from pathlib import Path

from core.contracts import AttackCategory
from tools.rag_store import RagStore

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "techniques" / "techniques.json"


def load_techniques() -> list[dict]:
    """Return the technique records (id, name, description, how_to, ...)."""
    return json.loads(_CATALOG_PATH.read_text())


def _embed_text(t: dict) -> str:
    return f"{t['name']}. {t['description']} {t['how_to']}"


def _metadata(t: dict) -> dict:
    md = {
        "kind": "technique",
        "technique_id": t["id"],
        "is_multi_turn": t["is_multi_turn"],
    }
    for cat in t["applicable_categories"]:
        md[f"cat_{cat}"] = True
    return md


async def index_techniques(store: RagStore) -> int:
    """Embed + upsert every technique into the shared store. Idempotent on id."""
    techs = load_techniques()
    records = [
        {"id": t["id"], "text": _embed_text(t), "metadata": _metadata(t)}
        for t in techs
    ]
    await store.add(records)
    return len(records)


async def retrieve_techniques(
    store: RagStore,
    category: AttackCategory,
    query_text: str,
    top_k: int = 3,
) -> list[dict]:
    """Top techniques for a category: metadata filter on category, semantic rank.

    Returns full technique records (with a `score`), nearest first. Empty if
    nothing applies / store empty.
    """
    cat = category.value if isinstance(category, AttackCategory) else str(category)
    results = await store.query(query_text, where={f"cat_{cat}": True}, top_k=top_k)
    by_id = {t["id"]: t for t in load_techniques()}
    out = []
    for r in results:
        tech = by_id.get(r["metadata"].get("technique_id"))
        if tech:
            out.append({**tech, "score": r["score"]})
    return out
