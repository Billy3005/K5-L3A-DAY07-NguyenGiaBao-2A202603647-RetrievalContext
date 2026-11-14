"""Read-only access to the Day 6 PostgreSQL + pgvector store (table `chunks`).

Day 7 never writes to the Day 6 index. Dense search is exact cosine (no ANN index),
exactly as in Day 6, so a metadata filter cannot lower recall.
"""
import hashlib
import json
from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from . import config

FILTERABLE = {"chapter": "chapter", "section": "section"}
COLUMNS = "chunk_id, document_id, source, page, chapter, chapter_title, section, start_char, end_char, text, content_hash"


class StoreError(RuntimeError):
    """Vector store unavailable or misconfigured; never replaced by fake results."""


class PgStore:
    def __init__(self, database_url: str = config.DATABASE_URL) -> None:
        try:
            self.conn = psycopg.connect(database_url, connect_timeout=5, autocommit=True)
            register_vector(self.conn)
        except psycopg.OperationalError as e:
            raise StoreError(f"cannot connect to Day 6 pgvector store ({e}). Is Docker running? "
                             "`docker compose -p day6_student_starter up -d --wait` in Day 6 starter/") from e
        dim = self.conn.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid='chunks'::regclass "
                                "AND attname='embedding'").fetchone()[0]
        if dim != config.EMBEDDING_DIM:
            raise StoreError(f"index has vector({dim}), Day 7 query model has {config.EMBEDDING_DIM} dims")

    def chunks(self, index: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(f"SELECT {COLUMNS}, embedding_model FROM chunks WHERE strategy=%s ORDER BY chunk_id",
                                 (index,))
        cols = [d.name for d in rows.description]
        out = [dict(zip(cols, r)) for r in rows.fetchall()]
        if not out:
            raise StoreError(f"index '{index}' is empty")
        models = {r["embedding_model"] for r in out}
        if models != {config.EMBEDDING_MODEL}:
            raise StoreError(f"index '{index}' was embedded with {models}, expected {config.EMBEDDING_MODEL}")
        return out

    def dense_search(self, index: str, query_vector: list[float], top_k: int,
                     filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        where, params = ["strategy = %s"], [index]
        for key, value in (filters or {}).items():
            if key not in FILTERABLE:
                raise ValueError(f"filter on '{key}' is not allowed")
            where.append(f"{FILTERABLE[key]} = %s")
            params.append(value)
        sql = (f"SELECT {COLUMNS}, 1 - (embedding <=> %s::vector) AS score FROM chunks "
               f"WHERE {' AND '.join(where)} ORDER BY embedding <=> %s::vector, chunk_id LIMIT %s")
        try:
            cur = self.conn.execute(sql, [query_vector, *params, query_vector, top_k])
        except psycopg.Error as e:
            raise StoreError(f"dense search failed: {e}") from e
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def to_chunk(row: dict[str, Any], index: str) -> dict[str, Any]:
    """Day 7 chunk contract (data/README.md): id, text, source_id, source, page, metadata."""
    return {"id": row["chunk_id"], "text": row["text"], "source_id": row["document_id"], "source": row["source"],
            "page": row["page"],
            "metadata": {"chapter": row["chapter"], "chapter_title": row["chapter_title"], "section": row["section"],
                         "start_char": row["start_char"], "end_char": row["end_char"], "index": index,
                         "content_hash": row["content_hash"]}}


def export(index: str) -> dict[str, Any]:
    """Write the index's chunks (no vectors) and a manifest that pins the index version."""
    store = PgStore()
    rows = store.chunks(index)
    chunks = [to_chunk(r, index) for r in rows]
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / f"chunks_{index}.jsonl"
    path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks), encoding="utf-8")
    version = hashlib.sha256("".join(f"{r['chunk_id']}:{r['content_hash']}\n" for r in rows).encode()).hexdigest()
    return {"index": index, "chunks": len(chunks), "embedding_model": config.EMBEDDING_MODEL,
            "dim": config.EMBEDDING_DIM, "index_version_sha256": version, "file": path.name}


def load_chunks(index: str) -> list[dict[str, Any]]:
    path = config.DATA_DIR / f"chunks_{index}.jsonl"
    if not path.exists():
        raise StoreError(f"{path} missing: run `python -m src.cli export` first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
