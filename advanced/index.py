"""Advanced challenge, step 3: build the search index and the retrievers.

Index units = text chunks + table units + figure units (caption + AI vision description).
  dense          multilingual-e5-base ("passage: " / "query: " prefixes, the Day 6 model), exact cosine
                 over a NumPy matrix (advanced/data/index/embeddings.npy, L2-normalised)
  bm25           the Day 7 BM25 (src/bm25.py) over the same index text
  hybrid         RRF (k=60) of 50 dense + 50 BM25 candidates
  hybrid_rerank  hybrid top-30 re-scored by cross-encoder ms-marco-MiniLM-L6-v2
Optional filter: content type (text / table / figure), chosen by the agent per search.

`python -m advanced.index` (re)builds the index and writes data/index/manifest.json.
"""
import hashlib
import json
import time
from functools import lru_cache

import numpy as np

from src.bm25 import BM25
from src.retrievers import _embedder, _reranker, embed_query

from .ingest import DATA

IDX = DATA / "index"
PASSAGE_PREFIX = "passage: "
DESC_HEADER = "[AI-generated description of the figure image (claude-haiku-5-5); verify against the original]"


def load_units() -> list[dict]:
    units = [json.loads(l) for l in open(DATA / "units.jsonl", encoding="utf-8")]
    desc = {}
    p = DATA / "figure_descriptions.jsonl"
    if p.exists():
        for l in open(p, encoding="utf-8"):
            r = json.loads(l)
            desc[r["id"]] = r["description"]
    out = []
    for u in units:
        text = u["text"]
        if u["type"] == "figure":
            d = desc.get(u["id"], "")
            text = f"{u['caption'] or '(uncaptioned image)'}\n{DESC_HEADER}\n{d}" if d else (u["caption"] or "")
            if not text.strip():
                continue
        out.append({**u, "index_text": text, "metadata": {"type": u["type"]}})
    return out


def build() -> None:
    units = load_units()
    IDX.mkdir(parents=True, exist_ok=True)
    t = time.perf_counter()
    emb = _embedder().encode([PASSAGE_PREFIX + u["index_text"] for u in units], batch_size=32,
                             normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True)
    np.save(IDX / "embeddings.npy", emb.astype(np.float32))
    with open(IDX / "units.jsonl", "w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    h = hashlib.sha256((IDX / "units.jsonl").read_bytes()).hexdigest()
    by = {}
    for u in units:
        by[u["type"]] = by.get(u["type"], 0) + 1
    manifest = {"units": len(units), "by_type": by, "embedding_model": "intfloat/multilingual-e5-base",
                "dim": int(emb.shape[1]), "passage_prefix": PASSAGE_PREFIX, "units_sha256": h,
                "build_seconds": round(time.perf_counter() - t, 1)}
    (IDX / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(manifest)


@lru_cache(maxsize=1)
def _index():
    units = [json.loads(l) for l in open(IDX / "units.jsonl", encoding="utf-8")]
    emb = np.load(IDX / "embeddings.npy")
    bm = BM25([{**u, "text": u["index_text"]} for u in units])
    return units, emb, bm


def unit_by_id() -> dict[str, dict]:
    return {u["id"]: u for u in _index()[0]}


class Searcher:
    def __init__(self, method: str, candidates: int = 50, rrf_k: int = 60, pool: int = 30) -> None:
        self.method, self.candidates, self.rrf_k, self.pool = method, candidates, rrf_k, pool

    def _dense(self, q, k, ftype):
        units, emb, _ = _index()
        s = emb @ np.asarray(embed_query(q), dtype=np.float32)
        order = np.argsort(-s)
        out = []
        for i in order:
            if ftype and units[i]["type"] != ftype:
                continue
            out.append({**units[i], "dense_score": float(s[i])})
            if len(out) >= k:
                break
        return out

    def _bm25(self, q, k, ftype):
        _, _, bm = _index()
        res = bm.search(q, k, {"type": ftype} if ftype else None)
        return [{**c, "text": c["index_text"], "bm25_score": s} for c, s in res]

    def search(self, query: str, top_k: int, ftype: str | None = None) -> list[dict]:
        if self.method == "dense":
            res = self._dense(query, top_k, ftype)
            for r in res:
                r["score"] = r["dense_score"]
        elif self.method == "bm25":
            res = self._bm25(query, top_k, ftype)
            for r in res:
                r["score"] = r["bm25_score"]
        else:
            fused: dict[str, dict] = {}
            for name, lst in (("dense", self._dense(query, self.candidates, ftype)),
                              ("bm25", self._bm25(query, self.candidates, ftype))):
                for rank, r in enumerate(lst, 1):
                    item = fused.setdefault(r["id"], {**r, "rrf_score": 0.0})
                    item["rrf_score"] += 1.0 / (self.rrf_k + rank)
                    item[f"{name}_rank"] = rank
            res = sorted(fused.values(), key=lambda r: (-r["rrf_score"], r["id"]))
            for r in res:
                r["score"] = r["rrf_score"]
            if self.method == "hybrid_rerank":
                pool = res[:self.pool]
                ce = _reranker().predict([(query, r["index_text"]) for r in pool])
                for r, s in zip(pool, ce):
                    r["pre_rerank_score"], r["score"] = r["score"], float(s)
                res = sorted(pool, key=lambda r: (-r["score"], r["id"])) + res[self.pool:]
            res = res[:top_k]
        for rank, r in enumerate(res, 1):
            r["rank"] = rank
        return res


if __name__ == "__main__":
    build()
