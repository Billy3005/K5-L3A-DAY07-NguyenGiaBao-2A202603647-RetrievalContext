"""Shared helpers: question loading with the test-split guard, JSON I/O."""
import json
from pathlib import Path
from typing import Any

from . import config


def load_questions(split: str, *, configs: list[str] | None = None, stage: str = "retrieval") -> list[dict]:
    """Return questions of one split. The test split is locked until selection.json exists and
    only the pre-registered baseline + selected configs may run on it."""
    if split == "test2":
        if not config.TEST2_PREREG.exists():
            raise SystemExit("test2 is locked: commit results/test2_preregistration.json first")
        prereg = json.loads(config.TEST2_PREREG.read_text(encoding="utf-8"))
        bad = [c for c in configs or [] if c not in prereg[stage]["configs"]]
        if bad:
            raise SystemExit(f"configs {bad} were not pre-registered for test2")
        return json.loads(config.TEST2_QUESTIONS.read_text(encoding="utf-8"))
    if split == "test":
        if not config.SELECTION.exists():
            raise SystemExit("test split is locked: commit results/selection.json (chosen on dev) first")
        sel = json.loads(config.SELECTION.read_text(encoding="utf-8"))
        allowed = set(sel[stage]["allowed_on_test"])
        bad = [c for c in configs or [] if c not in allowed]
        if bad:
            raise SystemExit(f"configs {bad} were not pre-registered for test ({sorted(allowed)})")
    qs = json.loads(config.QUESTIONS.read_text(encoding="utf-8"))
    return [q for q in qs if q["split"] == split]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
