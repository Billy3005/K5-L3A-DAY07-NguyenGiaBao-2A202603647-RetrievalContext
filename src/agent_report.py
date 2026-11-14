"""Aggregate graded agent traces with the starter's own `aggregate()` (starter/agent_metrics.py).

Labels: results/agent/<split>/labels/<config>.json, a JSON array of
  {query_id, answer_grade (0/1/2, answerable only), citation_support [bool per citation],
   abstention_correct (bool, unanswerable only), reason, label_source}
Labels are produced by reading each trace against the gold evidence; nothing here infers grounding.
Writes results/agent/<split>/<config>_summary.json and prints a markdown row.
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict

from . import config
from .common import read_jsonl

sys.path.insert(0, str(config.ROOT / "starter"))
from agent_metrics import aggregate  # noqa: E402  (starter script, unchanged)


def summarize(split: str, name: str) -> dict:
    d = config.RESULTS / "agent" / split
    traces = read_jsonl(d / f"{name}.jsonl")
    labels = json.loads((d / "labels" / f"{name}.json").read_text(encoding="utf-8"))
    cases = [{"id": t["query_id"], "split": split, "answerable": t["answerable"]} for t in traces]
    reviews = [{k: v for k, v in lab.items() if k in ("query_id", "answer_grade", "citation_support", "abstention_correct")}
               for lab in labels]
    out = aggregate(cases, traces, reviews)
    lab = {x["query_id"]: x for x in labels}
    by_type = defaultdict(list)
    for t in traces:
        if t["answerable"] and t["status"] != "error":
            by_type[t["type"]].append(lab[t["query_id"]]["answer_grade"])
    out["grounded_by_type"] = {k: f"{sum(v)}/{2 * len(v)}" for k, v in sorted(by_type.items())}
    ok = [t for t in traces if t["status"] != "error"]
    out["searches_distribution"] = dict(sorted(defaultdict(int, {}).items()))
    dist = defaultdict(int)
    for t in ok:
        dist[t["searches"]] += 1
    out["searches_distribution"] = dict(sorted(dist.items()))
    out["context_evidence"] = f"{sum(t.get('context_evidence', False) for t in ok if t['answerable'])}/" \
                              f"{sum(t['answerable'] for t in ok)}"
    out["cost_usd_total"] = round(sum(t["cost_usd"] for t in traces), 5)
    out["median_latency_s"] = round(statistics.median(t["elapsed_s"] for t in traces), 2)
    out["tokens"] = {"input": sum(t["usage"]["input_tokens"] for t in traces),
                     "output": sum(t["usage"]["output_tokens"] for t in traces)}
    out["label_sources"] = sorted({x.get("label_source", "?") for x in labels})
    (d / f"{name}_summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def md_row(split: str, name: str, s: dict) -> str:
    g, cv, ab, fa, tu = s["grounded_answer"], s["citation_validity"], s["abstention"], s["false_abstention"], s["tool_use"]
    cov = s["answer_citation_coverage"]
    return (f"| {name} / {split} | {tu['n']}/{tu['N']} | {s['searches_distribution']} | "
            f"{g['0']}/{g['1']}/{g['2']} → {g['mean']:.2f}/2 | {cv['n']}/{cv['N']} | {cov['n']}/{cov['N']} | "
            f"{ab['n']}/{ab['N']} | {fa['n']}/{fa['N']} | {s['context_evidence']} | "
            f"${s['cost_usd_total']:.4f} · {s['median_latency_s']} s |")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "test", "test2"), required=True)
    ap.add_argument("--configs", nargs="+", required=True)
    args = ap.parse_args()
    print("| Cấu hình / split | Tool use | Số lượt search | Grounded 0/1/2 → TB | Citation hợp lệ | Câu có citation "
          "| Abstention đúng | Từ chối nhầm | Context Evidence | Chi phí · trung vị |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name in args.configs:
        print(md_row(args.split, name, summarize(args.split, name)))


if __name__ == "__main__":
    main()
