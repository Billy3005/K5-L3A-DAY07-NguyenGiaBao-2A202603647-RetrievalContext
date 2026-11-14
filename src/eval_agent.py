"""Run agent configs on one split and save full traces.

The agent sees only the question text and the user-provided filter. Gold evidence is attached to the
trace AFTER the run, for grading only. Outputs per config:
  results/agent/<split>/<config>.jsonl       full trace per question
  results/agent/<split>/<config>_auto.json   automatic metrics (tool use, calls, context evidence, cost)
Human/LLM-assisted labels live in results/agent/<split>/labels/<config>.json (see src/agent_report.py).
"""
import argparse
import json
import statistics
import sys
from collections import Counter

from . import config
from .agent import Agent
from .common import load_questions, write_jsonl
from .metrics import groups_covered
from .retrievers import _chunk_map


def run(name: str, questions: list[dict], only: list[str] | None) -> list[dict]:
    agent = Agent(name)
    agent.retriever.warmup()
    rows = []
    for q in questions:
        if only and q["id"] not in only:
            continue
        out = agent.run(q["question"], q.get("filter"))
        row = {"query_id": q["id"], "split": q["split"], "type": q["type"], "answerable": q["answerable"],
               "config": name, "agent_cfg": agent.cfg, "question": q["question"], "filter": q.get("filter"), **out}
        # ---- post-hoc grading aids (never shown to the agent) ----
        cmap = _chunk_map(agent.retriever.index)
        ctx = [cmap[cid] for cid in out["context_ids"]]
        row["context"] = [{"id": c["id"], "page": c["page"], "chapter": c["metadata"]["chapter"], "text": c["text"]}
                          for c in ctx]
        if q["answerable"]:
            row["gold_expected_answer"] = q["expected_answer"]
            row["gold_evidence_groups"] = q["evidence_groups"]
            row["context_evidence"] = len(groups_covered(ctx, q)) == len(q["evidence_groups"])
        else:
            row["gold_absence_reason"] = q["absence_reason"]
        rows.append(row)
        print(f"{name} {q['id']:4} {out['status']:8} searches={out['searches']} "
              f"ctx_ev={row.get('context_evidence', '-')} ${out['cost_usd']:.5f} {out['elapsed_s']}s", flush=True)
    return rows


def auto_metrics(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["status"] != "error"]
    ans = [r for r in ok if r["answerable"]]
    una = [r for r in ok if not r["answerable"]]
    return {"n": len(rows), "errors": len(rows) - len(ok),
            "tool_use": f"{sum(r['searches'] > 0 for r in ok)}/{len(ok)}",
            "searches_distribution": dict(sorted(Counter(r["searches"] for r in ok).items())),
            "model_calls_mean": round(statistics.mean(r["usage"]["model_calls"] for r in ok), 2),
            "context_evidence": f"{sum(r['context_evidence'] for r in ans)}/{len(ans)}",
            "answered_on_answerable": f"{sum(r['status'] == 'answered' for r in ans)}/{len(ans)}",
            "abstained_on_unanswerable": f"{sum(r['status'] == 'abstain' for r in una)}/{len(una)}",
            "validation_errors": sum(e["event"] == "validation_error" for r in rows for e in r["events"]),
            "avg_context_chars": round(statistics.mean(r["context_chars"] for r in ok)),
            "input_tokens": sum(r["usage"]["input_tokens"] for r in rows),
            "output_tokens": sum(r["usage"]["output_tokens"] for r in rows),
            "cost_usd_total": round(sum(r["cost_usd"] for r in rows), 5),
            "cost_usd_per_q": round(statistics.mean(r["cost_usd"] for r in rows), 6),
            "median_latency_s": round(statistics.median(r["elapsed_s"] for r in rows), 2)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "test", "test2"), required=True)
    ap.add_argument("--configs", nargs="+", default=list(config.AGENT_CONFIGS))
    ap.add_argument("--only", nargs="+", help="debug: run a subset of question ids (output goes to *_debug)")
    ap.add_argument("--tag", default="", help="suffix for repeated runs, e.g. _run2")
    args = ap.parse_args()
    questions = load_questions(args.split, configs=args.configs, stage="agent")
    out_dir = config.RESULTS / "agent" / args.split
    for name in args.configs:
        rows = run(name, questions, args.only)
        suffix = "_debug" if args.only else args.tag
        write_jsonl(out_dir / f"{name}{suffix}.jsonl", rows)
        m = auto_metrics(rows)
        (out_dir / f"{name}{suffix}_auto.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        print(name, json.dumps(m))


if __name__ == "__main__":
    main()
