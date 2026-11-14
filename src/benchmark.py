"""Build and verify the Day 7 benchmark.

* Day 6 questions (22) all go to the Day 7 **dev** split: the Day 6 test split was already
  run and analysed post hoc, so it is not an independent holdout any more.
* New Day 7 questions (benchmark/day7_new_questions.json) add multi-hop dev questions,
  unanswerable questions and a brand-new **test** split.

Schema (one JSON object per question):
  id, split, type, origin, question, answerable, filter,
  answerable -> expected_answer, evidence_groups: [[{source_id, page, evidence}, ...], ...]
      every group is REQUIRED; alternatives inside a group are interchangeable.
      `gold` (= all alternatives of the first group) is kept for starter compatibility.
  unanswerable -> expected_behavior="search_and_abstain", absence_reason, absence_check
"""
import json
import re
import sys

from . import config
from .textnorm import match_key


def _day6_to_day7(q: dict) -> dict:
    alts = [{"source_id": q["gold_source_id"], "page": q["gold_page"], "evidence": q["evidence_quote"]}]
    alts += [{"source_id": q["gold_source_id"], "page": a["gold_page"], "evidence": a["evidence_quote"]}
             for a in q.get("alt_gold", [])]
    return {"id": q["id"], "split": "dev", "type": q["type"], "section": q["section"],
            "origin": f"day6:{q['split']}", "question": q["question"], "answerable": True,
            "expected_answer": q["expected_answer"], "evidence_groups": [alts], "gold": alts,
            "filter": q.get("filter")}


def build() -> list[dict]:
    day6 = [json.loads(line) for line in config.DAY6_QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    new = json.loads((config.BENCHMARK_DIR / "day7_new_questions.json").read_text(encoding="utf-8"))
    out = [_day6_to_day7(q) for q in day6]
    for q in new:
        q = dict(q, origin="day7")
        if q["type"] == "unanswerable":
            q.update(answerable=False, expected_behavior="search_and_abstain", filter=q.get("filter"))
        else:
            q["answerable"] = True
            q["evidence_groups"] = [[{"source_id": config.DOCUMENT_ID, **alt} for alt in group]
                                    for group in q["evidence_groups"]]
            q["gold"] = q["evidence_groups"][0]
        out.append(q)
    return out


def verify(questions: list[dict]) -> list[str]:
    """Machine checks. Returns a list of problems (empty = OK)."""
    pages = {}
    for line in config.DAY6_PAGES.read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        pages[p["page"]] = p
    page_keys = {n: match_key(p["text"]) for n, p in pages.items()}
    problems, ids = [], set()
    for q in questions:
        if q["id"] in ids:
            problems.append(f"{q['id']}: duplicate id")
        ids.add(q["id"])
        if q["split"] not in ("dev", "test", "test2"):
            problems.append(f"{q['id']}: bad split")
        if q.get("filter"):
            ch = q["filter"].get("chapter")
            if ch not in {p["chapter"] for p in pages.values()}:
                problems.append(f"{q['id']}: filter chapter {ch} not in corpus")
        if q["answerable"]:
            for gi, group in enumerate(q["evidence_groups"]):
                for alt in group:
                    if alt["page"] not in pages:
                        problems.append(f"{q['id']} g{gi}: page {alt['page']} not in corpus")
                    elif match_key(alt["evidence"]) not in page_keys[alt["page"]]:
                        problems.append(f"{q['id']} g{gi}: evidence not on page {alt['page']}")
                    if q.get("filter") and pages.get(alt["page"], {}).get("chapter") != q["filter"]["chapter"]:
                        problems.append(f"{q['id']}: filter would exclude gold page {alt['page']}")
                    # leakage guard: no 8 consecutive evidence words inside the question
                    ev, qk = match_key(alt["evidence"]).split(), match_key(q["question"])
                    if any(" ".join(ev[i:i + 8]) in qk for i in range(max(0, len(ev) - 7))):
                        problems.append(f"{q['id']}: question copies 8+ consecutive evidence words")
        else:
            for kw in q["absence_check"]["keywords"]:
                where = sorted(n for n, k in page_keys.items() if kw.lower() in k)
                q.setdefault("_absence_scan", {})[kw] = where
    # dev/test must not share an evidence sentence
    def ev_set(split):
        return {(a["page"], match_key(a["evidence"])) for q in questions if q["split"] == split and q["answerable"]
                for g in q["evidence_groups"] for a in g}
    shared = ev_set("dev") & ev_set("test")
    if shared:
        problems.append(f"dev/test share evidence: {shared}")
    return problems


def build_test2() -> None:
    """test2: a second, fresh holdout created after the first test was consumed (RULES.md:
    'Nếu đã xem test để chỉnh, tạo test mới'). Same schema and checks; additionally it must not
    share any evidence sentence with dev or test."""
    src = json.loads((config.TEST2_DIR / "questions_source.json").read_text(encoding="utf-8"))
    out = []
    for q in src:
        q = dict(q, split="test2", origin="day7-test2")
        if q["type"] == "unanswerable":
            q.update(answerable=False, expected_behavior="search_and_abstain", filter=q.get("filter"))
        else:
            q["answerable"] = True
            q["evidence_groups"] = [[{"source_id": config.DOCUMENT_ID, **a} for a in g] for g in q["evidence_groups"]]
            q["gold"] = q["evidence_groups"][0]
        out.append(q)
    main_qs = json.loads(config.QUESTIONS.read_text(encoding="utf-8"))
    problems = [p for p in verify(main_qs + out) if "dev/test share" not in p]
    old = {(a["page"], match_key(a["evidence"])) for q in main_qs if q["answerable"] for g in q["evidence_groups"] for a in g}
    new = {(a["page"], match_key(a["evidence"])) for q in out if q["answerable"] for g in q["evidence_groups"] for a in g}
    if old & new:
        problems.append(f"test2 shares evidence with dev/test: {old & new}")
    for q in out:
        if not q["answerable"]:
            print(f"[absence scan] {q['id']}: " + "; ".join(f"'{k}' on pages {v}" for k, v in q.pop("_absence_scan").items()))
    for q in main_qs:
        q.pop("_absence_scan", None)
    if problems:
        print("\n".join(problems))
        raise SystemExit("test2 verification FAILED")
    config.TEST2_QUESTIONS.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK: {len(out)} test2 questions ({sum(q['answerable'] for q in out)} answerable) -> "
          f"{config.TEST2_QUESTIONS.relative_to(config.ROOT)}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--test2" in sys.argv:
        build_test2()
        return
    questions = build()
    problems = verify(questions)
    for q in questions:
        if not q["answerable"]:
            print(f"[absence scan] {q['id']}: " + "; ".join(f"'{k}' on pages {v}" for k, v in q.pop("_absence_scan").items()))
    if problems:
        print("\n".join(problems))
        raise SystemExit("benchmark verification FAILED")
    config.QUESTIONS.write_text(json.dumps(questions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = {}
    for q in questions:
        key = (q["split"], "answerable" if q["answerable"] else "unanswerable")
        counts[key] = counts.get(key, 0) + 1
    print(f"OK: {len(questions)} questions written to {config.QUESTIONS.relative_to(config.ROOT)}", counts)


if __name__ == "__main__":
    main()
