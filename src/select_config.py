"""Apply the selection rules pre-registered in benchmark/README.md (commit a6ab742) to dev results
and write results/selection.json, which unlocks the test split for the allowed configs only."""
import csv
import json
import sys

from . import config


def frac(s: str) -> int:
    return int(s.split("/")[0])


def stage1() -> dict:
    rows = list(csv.DictReader((config.RESULTS / "retrieval" / "dev" / "metrics.csv").open(encoding="utf-8")))
    trace = []
    best = max(frac(r["hit3"]) for r in rows)
    cand = [r for r in rows if frac(r["hit3"]) >= best - 1]
    trace.append(f"rule 1 Hit@3 (best {best}, tie <=1): {[r['config'] for r in cand]}")
    for key, label in (("context_evidence", "rule 2 Context Evidence"), ("hit1", "rule 3 Hit@1")):
        if len(cand) > 1:
            top = max(frac(r[key]) for r in cand)
            cand = [r for r in cand if frac(r[key]) == top]
            trace.append(f"{label}: {[r['config'] for r in cand]}")
    if len(cand) > 1:
        cand = sorted(cand, key=lambda r: float(r["median_ms"]))[:1]
        trace.append(f"rule 4 median latency: {cand[0]['config']}")
    return {"selected": cand[0]["config"], "baseline": "dense_B", "trace": trace}


def stage2(names: list[str]) -> dict:
    d = config.RESULTS / "agent" / "dev"
    s = {n: json.loads((d / f"{n}_summary.json").read_text(encoding="utf-8")) for n in names}
    trace = []
    cand = [n for n in names if s[n]["abstention"]["n"] >= 3 and s[n]["provider_errors"] == 0]
    trace.append(f"rule 1 eligibility (abstention >= 3/4, no errors): {cand}")
    best = max(s[n]["grounded_answer"]["mean"] for n in cand)
    cand = [n for n in cand if s[n]["grounded_answer"]["mean"] >= best - 0.1]
    trace.append(f"rule 2 grounded mean (best {best:.2f}, tie <=0.1): {cand}")
    low = min(s[n]["false_abstention"]["n"] for n in cand)
    cand = [n for n in cand if s[n]["false_abstention"]["n"] == low]
    trace.append(f"rule 3 fewest false abstentions ({low}): {cand}")
    cost = {n: s[n]["cost_usd_total"] / s[n]["cases"] for n in cand}
    chosen = min(cand, key=lambda n: cost[n])
    trace.append(f"rule 4 cost per question: {', '.join(f'{n}=${c:.6f}' for n, c in sorted(cost.items(), key=lambda x: x[1]))}"
                 f" -> {chosen}")
    return {"selected": chosen, "baseline": "agent_dense_B", "trace": trace}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    s1 = stage1()
    s2 = stage2(list(config.AGENT_CONFIGS))
    selection = {
        "decided_on": "dev only", "rules": "benchmark/README.md, locked in commit a6ab742",
        "retrieval": {**s1, "allowed_on_test": [s1["baseline"], s1["selected"]]},
        "agent": {**s2, "allowed_on_test": [s2["baseline"], s2["selected"], "agent_hrr_B_1shot_v2"],
                  "secondary_reported_not_selectable": "agent_hrr_B_1shot_v2",
                  "secondary_reason": "Declared before test: reported only to check whether the v2 fixes "
                                      "(neighbor chunk + abstain rule) generalize; it cannot replace the selection."},
    }
    config.SELECTION.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
