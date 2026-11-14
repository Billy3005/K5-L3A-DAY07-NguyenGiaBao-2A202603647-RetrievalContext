"""Print agent runs compactly (for drafting labels): python -m advanced.dump <split> <config>"""
import json
import sys

split, cfg = sys.argv[1], sys.argv[2]
Q = {q["id"]: q for q in json.load(open("advanced/benchmark/questions.json", encoding="utf-8"))["questions"]}
for l in open(f"advanced/results/agent/{split}/{cfg}.jsonl", encoding="utf-8"):
    r = json.loads(l)
    q = Q[r["id"]]
    views = [e["unit"] for e in r["events"] if e["event"] == "view"]
    gold = [a["unit"] for g in q["evidence_groups"] for a in g]
    print(f"### {r['id']} [{q['group']}] {r['status']} s={r['searches']} v={views} ${r['cost_usd']} {r['elapsed_s']}s")
    print("EXP:", q["expected"][:260])
    print("ANS:", (r["answer"] if r["status"] == "answered" else r.get("abstain_reason") or r.get("error")))
    print("CIT:", r["citations"], "| GOLD:", gold, "| ctx-has-gold:", [g for g in gold if g in r["context_ids"]])
