"""Retrieval methods over ONE Day 6 index version.

  dense          e5 query embedding -> exact cosine in pgvector (Day 6 store)
  bm25           Okapi BM25 over the same chunks (exported from the same table)
  hybrid         Reciprocal Rank Fusion of dense + BM25 candidate lists
  hybrid_rerank  hybrid candidates re-scored by a cross-encoder

Every result: id, text, source_id, source, page, metadata, score, rank, method, and
the component ranks/scores that produced it. A user-provided `filters` dict
(e.g. {"chapter": 4}) is applied by every method as a pre-filter.
"""
import time
from functools import lru_cache
from typing import Any

from . import config
from .bm25 import BM25
from .store import PgStore, load_chunks


@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(config.EMBEDDING_MODEL, device="cpu")
    if model.get_sentence_embedding_dimension() != config.EMBEDDING_DIM:
        raise RuntimeError("query embedding dimension does not match the Day 6 index")
    return model


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(config.RERANK_MODEL, device="cpu")


@lru_cache(maxsize=1)
def _store() -> PgStore:
    return PgStore()


@lru_cache(maxsize=4)
def _bm25(index: str) -> BM25:
    return BM25(load_chunks(index))


@lru_cache(maxsize=4)
def _chunk_map(index: str) -> dict[str, dict]:
    return {c["id"]: c for c in load_chunks(index)}


def embed_query(text: str) -> list[float]:
    vec = _embedder().encode([config.QUERY_PREFIX + text], normalize_embeddings=True, convert_to_numpy=True)[0]
    return vec.tolist()


class Retriever:
    def __init__(self, name: str) -> None:
        if name not in config.RETRIEVAL_CONFIGS:
            raise ValueError(f"unknown retrieval config {name}")
        self.name, self.cfg = name, config.RETRIEVAL_CONFIGS[name]
        self.index = self.cfg["index"]

    def warmup(self) -> None:
        """Load models/indexes so that latency measurements exclude one-off loading."""
        _chunk_map(self.index)
        if self.cfg["method"] != "bm25":
            embed_query("warmup"); _store()
        if self.cfg["method"] != "dense":
            _bm25(self.index)
        if self.cfg["method"] == "hybrid_rerank":
            _reranker().predict([("warmup", "warmup")])

    # --- components -------------------------------------------------------
    def _dense(self, query: str, k: int, filters) -> list[dict]:
        rows = _store().dense_search(self.index, embed_query(query), k, filters)
        cmap = _chunk_map(self.index)
        out = []
        for r in rows:
            if r["chunk_id"] not in cmap:
                raise RuntimeError(f"{r['chunk_id']} in pgvector but not in export: re-run `python -m src.cli export`")
            out.append({**cmap[r["chunk_id"]], "dense_score": float(r["score"])})
        return out

    def _bm25(self, query: str, k: int, filters) -> list[dict]:
        return [{**c, "bm25_score": s} for c, s in _bm25(self.index).search(query, k, filters)]

    # --- public -----------------------------------------------------------
    def search(self, query: str, *, top_k: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        method = self.cfg["method"]
        if method == "dense":
            res = self._dense(query, top_k, filters)
            for r in res:
                r["score"] = r["dense_score"]
        elif method == "bm25":
            res = self._bm25(query, top_k, filters)
            for r in res:
                r["score"] = r["bm25_score"]
        else:
            n, k = self.cfg["candidates"], self.cfg["rrf_k"]
            dense, lex = self._dense(query, n, filters), self._bm25(query, n, filters)
            fused: dict[str, dict] = {}
            for name, lst in (("dense", dense), ("bm25", lex)):
                for rank, r in enumerate(lst, 1):
                    item = fused.setdefault(r["id"], {**{kk: vv for kk, vv in r.items() if not kk.endswith("_score")},
                                                      "rrf_score": 0.0})
                    item["rrf_score"] += 1.0 / (k + rank)
                    item[f"{name}_rank"] = rank
                    item[f"{name}_score"] = r[f"{name}_score"]
            res = sorted(fused.values(), key=lambda r: (-r["rrf_score"], r["id"]))
            for r in res:
                r["score"] = r["rrf_score"]
            if method == "hybrid_rerank":
                pool = res[:self.cfg["rerank_pool"]]
                ce = _reranker().predict([(query, r["text"]) for r in pool])
                for r, s in zip(pool, ce):
                    r["rerank_score"], r["pre_rerank_score"] = float(s), r["score"]
                    r["score"] = float(s)
                res = sorted(pool, key=lambda r: (-r["rerank_score"], r["id"])) + res[self.cfg["rerank_pool"]:]
            res = res[:top_k]
        for rank, r in enumerate(res, 1):
            r["rank"], r["method"], r["config"] = rank, method, self.name
        return res

    def timed_search(self, query: str, *, top_k: int, filters=None) -> tuple[list[dict], float]:
        t = time.perf_counter()
        res = self.search(query, top_k=top_k, filters=filters)
        return res, (time.perf_counter() - t) * 1000
