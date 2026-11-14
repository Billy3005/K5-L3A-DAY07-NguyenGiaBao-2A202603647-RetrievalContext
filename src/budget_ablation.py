"""POST-HOC diagnostic (added after the single test run; never used for selection).

Re-packs the stored top-10 retrieval results of each trace with other context budgets and
recomputes Context Evidence Rate. Deterministic, no retrieval or model call: it only asks
"how much evidence did the 4000-char budget throw away?".
"""
import csv
import json
import sys

from . import config
from .common import read_jsonl
from .metrics import groups_covered, pack_context
from .store import load_chunks

BUDGETS = (2000, 4000, 6000, 8000)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    questions = {q["id"]: q for q in json.loads(config.QUESTIONS.read_text(encoding="utf-8"))}
    cmaps = {ix: {c["id"]: c for c in load_chunks(ix)} for ix in config.INDEXES}
    rows = []
    for split in ("dev", "test"):
        for path in sorted((config.RESULTS / "retrieval" / split).glob("*.jsonl")):
            traces = [t for t in read_jsonl(path) if t["answerable"] and t["status"] == "ok"]
            row = {"split": split, "config": path.stem, "N": len(traces),
                   "hit3": sum(t["hit3"] for t in traces)}
            for b in BUDGETS:
                ok, chunks = 0, []
                for t in traces:
                    q = questions[t["query_id"]]
                    res = [cmaps[t["index"]][r["id"]] for r in t["results"]]  # exact chunks -> exact headers
                    _, kept = pack_context(res, b)
                    chunks.append(len(kept))
                    ok += len(groups_covered(kept, q)) == len(q["evidence_groups"])
                row[f"ctx_ev@{b}"] = f"{ok}/{len(traces)}"
                row[f"chunks@{b}"] = round(sum(chunks) / len(chunks), 1)
            rows.append(row)
            print(row)
    out = config.RESULTS / "retrieval" / "budget_ablation_posthoc.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out.relative_to(config.ROOT))


if __name__ == "__main__":
    main()
