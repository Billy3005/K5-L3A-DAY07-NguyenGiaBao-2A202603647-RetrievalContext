"""Write label files from a compact grading spec: default = grade 2 / all citations supported /
abstention correct when status == abstain; exceptions listed explicitly with reasons."""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
split = sys.argv[2]
spec = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
SOURCE = spec["label_source"]

for cfg, exceptions in spec["configs"].items():
    traces = [json.loads(l) for l in (ROOT / "results/agent" / split / f"{cfg}.jsonl").read_text(encoding="utf-8").splitlines()]
    labels = []
    for t in traces:
        exc = exceptions.get(t["query_id"], {})
        lab = {"query_id": t["query_id"], "status": t["status"], "label_source": SOURCE}
        support = [True] * len(t["citations"])
        for idx in exc.get("unsupported_citation_idx", []):
            support[idx] = False
        lab["citation_support"] = support
        if t["status"] == "error":
            continue
        if t["answerable"]:
            lab["answer_grade"] = exc.get("grade", 0 if t["status"] == "abstain" else 2)
        else:
            lab["abstention_correct"] = exc.get("abstention_correct", t["status"] == "abstain")
        lab["reason"] = exc.get("reason", spec["default_reason"]["answerable" if t["answerable"] else "unanswerable"])
        labels.append(lab)
    out = ROOT / "results/agent" / split / "labels" / f"{cfg}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(labels, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(cfg, len(labels), "labels")
