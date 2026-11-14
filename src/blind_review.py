"""Blind second annotation by the student (does NOT show the LLM labels).

  python -m src.blind_review make     # writes results/agent/BLIND_REVIEW.md + blind_review.csv (empty grades)
  python -m src.blind_review score    # after the student fills the CSV: agreement + Cohen's kappa vs LLM labels

Items: every test question answered by the SELECTED agent (agent_hrr_B_1shot), 15 items.
"""
import csv
import json
import sys
from collections import Counter

from . import config
from .common import read_jsonl

CFG, SPLIT = "agent_hrr_B_1shot", "test"
# Items of this config whose LLM label the student already saw in REVIEW.md (not blind).
SEEN_IN_REVIEW = {"t01", "t05", "t10", "t11", "ut1"}
D = config.RESULTS / "agent"
CSV = D / "blind_review.csv"


def make() -> None:
    traces = read_jsonl(D / SPLIT / f"{CFG}.jsonl")
    chunks = {}
    for line in (config.DATA_DIR / "chunks_B.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        chunks[c["id"]] = c
    md = ["# Chấm mù (học viên) — không xem nhãn LLM trước khi điền", "",
          f"Cấu hình `{CFG}`, split `{SPLIT}`, {len(traces)} câu. Với mỗi câu: đọc câu trả lời, đọc toàn văn chunk được trích, "
          "rồi điền vào `results/agent/blind_review.csv`:",
          "- `student_grade`: 0/1/2 cho câu có đáp án (từ chối câu có đáp án = 0); để trống cho câu thiếu evidence",
          "- `student_abstention_ok`: yes/no cho câu thiếu evidence",
          "- `student_citations_ok`: số citation hỗ trợ đúng câu được gắn (ví dụ 2/2)",
          "Sau đó chạy `python -m src.blind_review score`. **Không mở `labels/` hay `grading_spec_test.json` trước khi điền xong.**",
          f"Lưu ý: {sorted(SEEN_IN_REVIEW)} đã xuất hiện kèm nhãn LLM trong REVIEW.md, nên script báo đồng thuận "
          "riêng cho các câu còn lại (thật sự mù).", ""]
    rows = []
    for t in traces:
        md += [f"## {t['query_id']} ({t['type']}{', filter ' + json.dumps(t['filter']) if t['filter'] else ''})",
               f"**Câu hỏi:** {t['question']}", "",
               f"**Đáp án chuẩn / hành vi mong đợi:** {t.get('gold_expected_answer') or 'TỪ CHỐI — ' + t['gold_absence_reason']}", "",
               f"**Agent ({t['status']}):** {t['answer'] if t['status'] == 'answered' else t.get('abstain_reason', '')}", ""]
        for cid in t["citations"]:
            md += [f"> **[{cid}]** (trang {chunks[cid]['page']})", ">", "> " + chunks[cid]["text"].replace("\n", "\n> "), ""]
        rows.append({"query_id": t["query_id"], "answerable": t["answerable"], "status": t["status"],
                     "n_citations": len(t["citations"]), "student_grade": "", "student_abstention_ok": "",
                     "student_citations_ok": "", "notes": ""})
    (D / "BLIND_REVIEW.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} items to BLIND_REVIEW.md and blind_review.csv")


def kappa(pairs: list[tuple]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def score() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    llm = {x["query_id"]: x for x in json.loads((D / SPLIT / "labels" / f"{CFG}.json").read_text(encoding="utf-8"))}
    pairs, disagreements = [], []
    for r in rows:
        lab = llm[r["query_id"]]
        if r["answerable"] == "True":
            if not r["student_grade"].strip():
                raise SystemExit(f"{r['query_id']}: student_grade empty")
            a, b = int(r["student_grade"]), lab["answer_grade"]
        else:
            if not r["student_abstention_ok"].strip():
                raise SystemExit(f"{r['query_id']}: student_abstention_ok empty")
            a, b = r["student_abstention_ok"].strip().lower() == "yes", lab["abstention_correct"]
        pairs.append((str(a), str(b)))
        if a != b:
            disagreements.append({"query_id": r["query_id"], "student": a, "llm": b, "notes": r["notes"]})
    blind = [p for p, r in zip(pairs, rows) if r["query_id"] not in SEEN_IN_REVIEW]
    out = {"items": len(pairs), "exact_agreement": f"{sum(a == b for a, b in pairs)}/{len(pairs)}",
           "cohen_kappa": kappa(pairs),
           "truly_blind_items": len(blind), "truly_blind_agreement": f"{sum(a == b for a, b in blind)}/{len(blind)}",
           "truly_blind_kappa": kappa(blind), "seen_before_in_REVIEW": sorted(SEEN_IN_REVIEW),
           "disagreements": disagreements,
           "note": "Student graded blind (LLM labels hidden). Kappa over grade levels 0/1/2 and abstention yes/no."}
    (D / "blind_agreement.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"make": make, "score": score}[sys.argv[1]]()
