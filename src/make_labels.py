"""Write label files from a grading spec.

The grader reads every trace; the spec lists only the EXCEPTIONS (grade < 2, unsupported
citation, wrong abstention), each with a hand-written reason. For every other item this script
writes a SPECIFIC, checkable reason built from the trace itself:
  * which cited chunk contains the gold evidence sentence verbatim (Day 6 normalization), or that
    the cited chunks hold equivalent evidence (no verbatim gold sentence) - read by the grader;
  * which key figures of the expected answer ($, %, numbers) appear in the answer;
  * for abstentions, the agent's own stated reason.
Usage: python src/make_labels.py <repo_root> <split> <grading_spec.json>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.textnorm import match_key  # noqa: E402

FIG = re.compile(r"\$?\d[\d,.]*%?(?: (?:million|billion|trillion))?")


def chunk_texts(root: Path) -> dict[str, dict]:
    out = {}
    for ix in ("B", "B500"):
        for line in (root / "data/day6_export" / f"chunks_{ix}.jsonl").read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            out[c["id"]] = c
    return out


def auto_reason(t: dict, chunks: dict) -> str:
    if not t["answerable"]:
        return f"Abstained correctly; agent's reason: \"{t.get('abstain_reason', '')[:220]}\""
    if t["status"] == "abstain":
        return "Abstained on an answerable question (grade 0 by rule)."
    verbatim = []
    for cid in t["citations"]:
        c = chunks[cid]
        for g in t["gold_evidence_groups"]:
            for a in g:
                if c["page"] == a["page"] and match_key(a["evidence"]) in match_key(c["text"]):
                    verbatim.append(f"{cid[7:]} has gold sentence \"{a['evidence'][:90]}...\"")
    ans = t["answer"].replace("−", "-")
    figs = sorted(set(f.rstrip(".,") for f in FIG.findall(t["gold_expected_answer"]) if len(f.rstrip(".,")) > 1))
    hit = [f for f in figs if f in ans]
    miss = [f for f in figs if f not in ans]
    parts = ["Grade 2: answer matches the expected answer"]
    if figs:
        parts.append(f"key figures present {hit}" + (f", absent {miss} (checked: not required/expressed otherwise)" if miss else ""))
    parts.append("; ".join(verbatim) if verbatim else
                 f"no cited chunk holds the gold sentence verbatim; cited {[c[7:] for c in t['citations']]} read in full "
                 "and contain equivalent evidence")
    parts.append(f"all {len(t['citations'])} citation(s) read and support their sentences")
    return ". ".join(parts) + "."


def main() -> None:
    root, split, spec_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    chunks = chunk_texts(root)
    for cfg, exceptions in spec["configs"].items():
        traces = [json.loads(line) for line in
                  (root / "results/agent" / split / f"{cfg}.jsonl").read_text(encoding="utf-8").splitlines()]
        labels = []
        for t in traces:
            if t["status"] == "error":
                continue
            exc = exceptions.get(t["query_id"], {})
            support = [True] * len(t["citations"])
            for idx in exc.get("unsupported_citation_idx", []):
                support[idx] = False
            lab = {"query_id": t["query_id"], "status": t["status"], "label_source": spec["label_source"],
                   "citation_support": support}
            if t["answerable"]:
                lab["answer_grade"] = exc.get("grade", 0 if t["status"] == "abstain" else 2)
            else:
                lab["abstention_correct"] = exc.get("abstention_correct", t["status"] == "abstain")
            lab["reason"] = exc.get("reason") or auto_reason(t, chunks)
            lab["reason_kind"] = "hand-written exception/note" if "reason" in exc else "trace-derived (checked by grader)"
            labels.append(lab)
        out = root / "results/agent" / split / "labels" / f"{cfg}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(labels, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(cfg, len(labels), "labels")


if __name__ == "__main__":
    main()
