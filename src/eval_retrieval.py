"""Retrieval-only benchmark: same corpus/index version/questions/labels for every config.

Original question text is the query (no rewriting). Answerable questions only enter the
metric denominators; unanswerable ones are still retrieved and traced (for inspection).
Writes results/retrieval/<split>/<config>.jsonl and results/retrieval/<split>/metrics.csv.
"""
import argparse
import csv
import statistics
import sys

from . import config
from .common import load_questions, write_jsonl
from .metrics import groups_covered, pack_context, ranking_metrics
from .retrievers import Retriever


def run_config(name: str, questions: list[dict]) -> tuple[list[dict], dict]:
    retriever = Retriever(name)
    retriever.warmup()
    traces = []
    for q in questions:
        row = {"query_id": q["id"], "split": q["split"], "type": q["type"], "answerable": q["answerable"],
               "config": name, "method": retriever.cfg["method"], "index": retriever.index,
               "query": q["question"], "query_kind": "original", "filter": q.get("filter"),
               "top_k": config.EVAL_TOP_K, "budget_chars": config.CONTEXT_BUDGET_CHARS}
        try:
            results, ms = retriever.timed_search(q["question"], top_k=config.EVAL_TOP_K, filters=q.get("filter"))
        except Exception as e:  # recorded, never replaced by fake results
            row.update(status="error", error=f"{type(e).__name__}: {e}")
            traces.append(row)
            continue
        context, kept = pack_context(results, config.CONTEXT_BUDGET_CHARS)
        row.update(status="ok", elapsed_ms=round(ms, 1), context_ids=[r["id"] for r in kept],
                   context_chars=len(context))
        if q["answerable"]:
            m = ranking_metrics(results, q)
            row.update({k: m[k] for k in ("hit1", "hit3", "full3", "rr10", "first_hit_rank", "gold_page_in_top3")})
            row["context_evidence"] = len(groups_covered(kept, q)) == len(q["evidence_groups"])
            hit_groups = m["hit_groups_per_rank"]
        else:
            hit_groups = [[] for _ in results]
        row["results"] = [{"rank": r["rank"], "id": r["id"], "page": r["page"], "chapter": r["metadata"]["chapter"],
                           "section": r["metadata"]["section"], "score": round(r["score"], 6),
                           **{k: (round(r[k], 6) if isinstance(r[k], float) else r[k])
                              for k in ("dense_rank", "bm25_rank", "dense_score", "bm25_score", "pre_rerank_score")
                              if k in r},
                           "hit_groups": h, "text": r["text"]} for r, h in zip(results, hit_groups)]
        traces.append(row)
    ok = [t for t in traces if t["status"] == "ok"]
    ans = [t for t in ok if t["answerable"]]
    n = sum(q["answerable"] for q in questions)

    def frac(key):
        return f"{sum(bool(t[key]) for t in ans)}/{n}"
    summary = {"config": name, "split": questions[0]["split"], "method": retriever.cfg["method"],
               "index": retriever.index, "N_answerable": n, "errors": len(traces) - len(ok),
               "hit1": frac("hit1"), "hit3": frac("hit3"), "full3": frac("full3"),
               "mrr10": round(sum(t["rr10"] for t in ans) / n, 3) if n else None,
               "context_evidence": frac("context_evidence"),
               "avg_context_chars": round(statistics.mean(t["context_chars"] for t in ok)),
               "avg_context_chunks": round(statistics.mean(len(t["context_ids"]) for t in ok), 2),
               "median_ms": round(statistics.median(t["elapsed_ms"] for t in ok), 1),
               "p90_ms": round(sorted(t["elapsed_ms"] for t in ok)[int(0.9 * (len(ok) - 1))], 1),
               "cost_usd": 0.0, "hypothesis": retriever.cfg["hypothesis"]}
    return traces, summary


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "test"), required=True)
    ap.add_argument("--configs", nargs="+", default=list(config.RETRIEVAL_CONFIGS))
    args = ap.parse_args()
    questions = load_questions(args.split, configs=args.configs, stage="retrieval")
    out_dir = config.RESULTS / "retrieval" / args.split
    summaries = []
    for name in args.configs:
        traces, summary = run_config(name, questions)
        write_jsonl(out_dir / f"{name}.jsonl", traces)
        summaries.append(summary)
        print({k: v for k, v in summary.items() if k != "hypothesis"})
    path = out_dir / "metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summaries[0]))
        w.writeheader()
        w.writerows(summaries)
    print(f"wrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
