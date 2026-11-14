"""Labels, review sheet and scores for the advanced benchmark.

  python -m advanced.review sheet --split test --config adv_hrr_view
      -> results/review/<split>_<config>.md : per question the question, expected answer, the agent's
         answer and citations, and crops of the ORIGINAL page regions (cited units + gold units) so a
         person can check every label against the PDF; plus <split>_<config>_labels.csv to fill in.
  python -m advanced.review score --split test --config adv_hrr_view
      -> results/agent/<split>/<config>_score.json and a markdown table (n/N overall and per group,
         errors, time, cost).

Label sources: results/labels/<split>_<config>.json holds the LLM-drafted label and reason for every
question (drafted by Claude Code from the trace and the original page crops). The CSV column
`student_label` (pass/fail) overrides it when filled; `labeled_by` records which one counted.
"""
import argparse
import csv
import json
from pathlib import Path


from .agent import render_region
from .index import unit_by_id

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
GROUPS = ["table", "diagram", "chart", "multihop", "text", "unanswerable"]


def _questions(split):
    return {q["id"]: q for q in json.load(open(ROOT / "benchmark" / "questions.json", encoding="utf-8"))["questions"]
            if q["split"] == split}


def _runs(split, config):
    return [json.loads(l) for l in open(RES / "agent" / split / f"{config}.jsonl", encoding="utf-8")]


def sheet(split, config):
    qs, runs, units = _questions(split), _runs(split, config), unit_by_id()
    llm = json.load(open(RES / "labels" / f"{split}_{config}.json", encoding="utf-8"))["labels"]
    out = RES / "review"
    img = out / f"img_{split}"
    img.mkdir(parents=True, exist_ok=True)
    lines = [f"# Review sheet — {split} — {config}", "",
             "For each question: read the agent's answer, open the crops (they are cut from the original PDF page, "
             "not from extracted text), compare with the expected answer, then write `pass` or `fail` in "
             f"`{split}_{config}_labels.csv` → column `student_label` (and a note if you disagree with the draft).", ""]
    rows = []
    for r in runs:
        q = qs[r["id"]]
        lab = llm[r["id"]]
        lines += [f"## {r['id']} · {q['group']} · draft label: **{lab['label'].upper()}**", "",
                  f"**Question:** {q['question']}", "", f"**Expected:** {q['expected']}", ""]
        if q.get("tolerance"):
            lines += [f"**Tolerance:** {q['tolerance']}", ""]
        lines += [f"**Agent ({r['status']}):** {r['answer']}", ""]
        if r.get("abstain_reason"):
            lines += [f"**Abstain reason:** {r['abstain_reason']}", ""]
        if q.get("check"):
            lines += [f"**How absence was checked:** {q['check']}", ""]
        lines += [f"**Draft reason:** {lab['reason']}", ""]
        shown = []
        for c in r.get("citation_details", []):
            shown.append((c["unit"], "cited"))
        for g in q["evidence_groups"]:
            for a in g:
                if a["unit"] not in [s[0] for s in shown]:
                    shown.append((a["unit"], "gold"))
        for e in r["events"]:
            if e["event"] == "view" and e["unit"] not in [s[0] for s in shown]:
                shown.append((e["unit"], "viewed by agent"))
        for uid, kind in shown:
            u = units.get(uid)
            if not u:
                continue
            p = img / f"{r['id']}_{uid}.png"
            p.write_bytes(render_region(u))
            lines += [f"*{kind}: `{uid}` — {u['type']} {u['label']} — PDF page {u['page']} (printed {u['printed_page']})*", "",
                      f"![{uid}](img_{split}/{p.name})", ""]
        lines += ["---", ""]
        rows.append({"id": r["id"], "group": q["group"], "agent_status": r["status"], "draft_label": lab["label"],
                     "student_label": "", "student_note": ""})
    (out / f"{split}_{config}.md").write_text("\n".join(lines), encoding="utf-8")
    csv_path = out / f"{split}_{config}_labels.csv"
    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print("wrote", out / f"{split}_{config}.md", "and", csv_path)


def score(split, config):
    qs, runs = _questions(split), _runs(split, config)
    llm = json.load(open(RES / "labels" / f"{split}_{config}.json", encoding="utf-8"))["labels"]
    student = {}
    csv_path = RES / "review" / f"{split}_{config}_labels.csv"
    if csv_path.exists():
        for row in csv.DictReader(open(csv_path, encoding="utf-8")):
            if row["student_label"].strip():
                student[row["id"]] = (row["student_label"].strip().lower(), row["student_note"])
    per, final = {g: [0, 0] for g in GROUPS}, {}
    for r in runs:
        lab, src = llm[r["id"]]["label"], "llm_draft"
        if r["id"] in student:
            lab, src = student[r["id"]][0], "student"
        ok = lab == "pass" and r["status"] != "error"
        final[r["id"]] = {"label": "pass" if ok else "fail", "labeled_by": src, "status": r["status"],
                          "llm_draft": llm[r["id"]]["label"], "reason": llm[r["id"]]["reason"],
                          "student_note": student.get(r["id"], ("", ""))[1]}
        per[qs[r["id"]]["group"]][0] += ok
        per[qs[r["id"]]["group"]][1] += 1
    n = len(runs)
    passed = sum(v["label"] == "pass" for v in final.values())
    res = {"split": split, "config": config, "pass": passed, "n": n, "pass_rate": round(passed / n, 4),
           "by_group": {g: f"{a}/{b}" for g, (a, b) in per.items() if b},
           "errors": sum(r["status"] == "error" for r in runs),
           "student_labels": len(student), "student_changed_draft": sum(1 for k, (s, _) in student.items() if s != llm[k]["label"]),
           "mean_s": round(sum(r["elapsed_s"] for r in runs) / n, 1), "p_max_s": max(r["elapsed_s"] for r in runs),
           "cost_usd": round(sum(r["cost_usd"] for r in runs), 4),
           "mean_searches": round(sum(r["searches"] for r in runs) / n, 2),
           "mean_views": round(sum(r.get("views", 0) for r in runs) / n, 2), "labels": final}
    (RES / "agent" / split / f"{config}_score.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "labels"}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["sheet", "score"])
    ap.add_argument("--split", required=True)
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    (sheet if a.what == "sheet" else score)(a.split, a.config)


if __name__ == "__main__":
    main()
