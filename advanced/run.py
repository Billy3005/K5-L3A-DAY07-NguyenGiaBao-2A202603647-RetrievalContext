"""Run retrieval and agent benchmarks for the advanced challenge.

  python -m advanced.run retrieval --split dev
  python -m advanced.run agent --split dev --configs adv_dense adv_hrr adv_hrr_view [--tag _run2]
  python -m advanced.run agent --split test --configs <the selected config>   (needs results/selection.json)

Retrieval metrics use the question text as the query, no content-type filter, top 10:
  hit1 / hit3: a unit from any evidence group at rank 1 / in top 3
  full5: every evidence group covered in the top 5;  rr10: reciprocal rank of the first hit
Agent traces (every search, view, answer, citation, tokens, cost, time, error) go to
advanced/results/agent/<split>/<config><tag>.jsonl. Labels are added afterwards by a person.
"""
import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
SELECTION = RES / "selection.json"


def load_questions(split: str) -> list[dict]:
    qs = [q for q in json.load(open(ROOT / "benchmark" / "questions.json", encoding="utf-8"))["questions"] if q["split"] == split]
    if not qs:
        raise SystemExit(f"no questions for split {split}")
    return qs


def gold_units(q: dict) -> list[set[str]]:
    return [{a["unit"] for a in g} for g in q["evidence_groups"]]


def retrieval(split: str) -> None:
    from .index import Searcher
    qs = [q for q in load_questions(split) if q["answerable"]]
    out = RES / "retrieval" / split
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for method in ["dense", "bm25", "hybrid", "hybrid_rerank"]:
        s = Searcher(method)
        s.search("warmup", 3)
        recs, lat = [], []
        for q in qs:
            t = time.perf_counter()
            res = s.search(q["question"], 10)
            lat.append((time.perf_counter() - t) * 1000)
            groups = gold_units(q)
            hits = [[gi for gi, g in enumerate(groups) if r["id"] in g] for r in res]
            first = next((i + 1 for i, h in enumerate(hits) if h), None)
            m = {"hit1": bool(hits[0]), "hit3": any(hits[:3]),
                 "full5": len({g for h in hits[:5] for g in h}) == len(groups), "rr10": 1 / first if first else 0.0}
            recs.append({"id": q["id"], "group": q["group"], **m, "first_hit_rank": first,
                         "top10": [{"rank": r["rank"], "id": r["id"], "type": r["type"], "score": round(r["score"], 4)} for r in res]})
        with open(out / f"{method}.jsonl", "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n = len(recs)
        rows.append({"method": method, "n": n, **{k: f"{sum(r[k] for r in recs)}/{n}" for k in ["hit1", "hit3", "full5"]},
                     "mrr10": round(sum(r["rr10"] for r in recs) / n, 3), "p50_ms": round(sorted(lat)[n // 2], 1)})
    with open(out / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


def agent(split: str, configs: list[str], tag: str, workers: int) -> None:
    from .agent import Agent
    from .index import Searcher
    if split == "test":
        if not SELECTION.exists():
            raise SystemExit("test is locked: run dev and write results/selection.json first")
        allowed = set(json.load(open(SELECTION, encoding="utf-8"))["test_configs"])
        if set(configs) - allowed:
            raise SystemExit(f"configs not selected for test: {set(configs) - allowed}")
    Searcher("hybrid_rerank").search("warmup", 3)
    Searcher("dense").search("warmup", 3)
    qs = load_questions(split)
    out = RES / "agent" / split
    out.mkdir(parents=True, exist_ok=True)
    for name in configs:
        ag = Agent(name)
        t = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            runs = list(ex.map(lambda q: (q, ag.run(q["question"])), qs))
        cost = 0.0
        with open(out / f"{name}{tag}.jsonl", "w", encoding="utf-8") as f:
            for q, r in runs:
                cost += r["cost_usd"]
                f.write(json.dumps({"id": q["id"], "group": q["group"], "answerable": q["answerable"],
                                    "question": q["question"], "config": name, **r}, ensure_ascii=False) + "\n")
        st = {}
        for _, r in runs:
            st[r["status"]] = st.get(r["status"], 0) + 1
        print(f"{name}{tag}: {st}  cost ${cost:.4f}  wall {time.perf_counter() - t:.0f}s")


def main() -> None:
    load_dotenv(ROOT.parent / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["retrieval", "agent"])
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--configs", nargs="*", default=["adv_dense", "adv_hrr", "adv_hrr_view"])
    ap.add_argument("--tag", default="")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.what == "retrieval":
        if a.split == "test" and not SELECTION.exists():
            raise SystemExit("test is locked until results/selection.json exists")
        retrieval(a.split)
    else:
        agent(a.split, a.configs, a.tag, a.workers)


if __name__ == "__main__":
    sys.exit(main())
