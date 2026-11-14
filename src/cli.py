"""Small utility commands.

  python -m src.cli export            # dump Day 6 index B and B500 chunks + manifest
  python -m src.cli search "question" --config hybrid_B [--chapter 4] [--k 5]
"""
import argparse
import json
import sys

from . import config
from .store import export


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--config", default="dense_B", choices=list(config.RETRIEVAL_CONFIGS))
    s.add_argument("--chapter", type=int)
    s.add_argument("--k", type=int, default=5)
    args = ap.parse_args()
    if args.cmd == "export":
        manifest = [export(index) for index in config.INDEXES]
        (config.DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, indent=2))
    else:
        from .retrievers import Retriever
        r = Retriever(args.config)
        res, ms = r.timed_search(args.query, top_k=args.k, filters={"chapter": args.chapter} if args.chapter else None)
        print(f"{len(res)} results in {ms:.0f} ms")
        for x in res:
            print(f"#{x['rank']} {x['id']} p{x['page']} score={x['score']:.4f} | {x['text'][:140]!r}")


if __name__ == "__main__":
    main()
