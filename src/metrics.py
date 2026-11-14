"""Evidence matching, ranking metrics and context packing (definitions: benchmark/README.md)."""
from typing import Any

from .textnorm import match_key


def chunk_hits(chunk: dict, question: dict) -> list[int]:
    """Indices of evidence groups that this chunk satisfies."""
    text = match_key(chunk["text"])
    out = []
    for gi, group in enumerate(question.get("evidence_groups", [])):
        if any(chunk["source_id"] == a["source_id"] and chunk["page"] == a["page"] and match_key(a["evidence"]) in text
               for a in group):
            out.append(gi)
    return out


def groups_covered(chunks: list[dict], question: dict) -> set[int]:
    return {g for c in chunks for g in chunk_hits(c, question)}


def ranking_metrics(results: list[dict], question: dict) -> dict[str, Any]:
    n_groups = len(question["evidence_groups"])
    hits = [chunk_hits(r, question) for r in results]
    first = next((i + 1 for i, h in enumerate(hits) if h), None)
    gold_pages = {a["page"] for g in question["evidence_groups"] for a in g}
    return {"hit1": bool(hits and hits[0]), "hit3": any(hits[:3]),
            "full3": len({g for h in hits[:3] for g in h}) == n_groups,
            "rr10": 1.0 / first if first and first <= 10 else 0.0, "first_hit_rank": first,
            "gold_page_in_top3": any(r["page"] in gold_pages for r in results[:3]),
            "hit_groups_per_rank": hits}


def pack_context(results: list[dict], budget_chars: int) -> tuple[str, list[dict]]:
    """Rank order, dedup by id, add whole chunks while they fit; never cut a chunk."""
    blocks, kept, seen = [], [], set()
    for r in results:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        block = format_chunk(r)
        if len("\n\n".join(blocks + [block])) <= budget_chars:
            blocks.append(block)
            kept.append(r)
    return "\n\n".join(blocks), kept


def format_chunk(r: dict) -> str:
    m = r["metadata"]
    return (f"[{r['id']}] (source: {r['source']}, page {r['page']}, chapter {m['chapter']}, "
            f"section: {m['section']})\n{r['text']}")
