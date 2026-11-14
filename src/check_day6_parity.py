"""Prove the Day 6 connection: Day 7 `dense_B` must return the same top-3 chunk ids as Day 6
strategy C (index B + chapter filter) for every Day 6 question.

Reads Day 6 traces (<DAY6_DIR>/starter/results/traces/{dev,test}.jsonl) and the Day 7 dense_B
traces (results/retrieval/dev/dense_B.jsonl, which contain all 22 Day 6 questions), and writes
results/day6_parity.json.
"""
import json
import sys

from . import config
from .common import read_jsonl


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    day6 = {}
    for name in ("dev.jsonl", "test.jsonl"):
        for t in read_jsonl(config.DAY6_DIR / "starter" / "results" / "traces" / name):
            if t["strategy"] == "C":
                day6[t["id"]] = [h["chunk_id"] for h in t["hits"]][:3]
    day7 = {t["query_id"]: [r["id"] for r in t["results"]][:3]
            for t in read_jsonl(config.RESULTS / "retrieval" / "dev" / "dense_B.jsonl")}
    rows = [{"id": q, "day6_top3": ids, "day7_top3": day7[q], "identical": ids == day7[q]} for q, ids in sorted(day6.items())]
    out = {"compared": len(rows), "identical": sum(r["identical"] for r in rows),
           "day6_source": "Day 6 starter/results/traces/{dev,test}.jsonl, strategy C",
           "day7_source": "results/retrieval/dev/dense_B.jsonl", "rows": rows}
    (config.RESULTS / "day6_parity.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"identical top-3: {out['identical']}/{out['compared']}")
    if out["identical"] != out["compared"]:
        raise SystemExit("Day 6 parity FAILED")


if __name__ == "__main__":
    main()
