"""Advanced challenge, step 2: vision descriptions for every figure unit (charts, diagrams, photos).

Each figure region (image bbox, 6pt padding) is rendered at 150 dpi and sent with its printed
caption to claude-haiku-5-5. The model transcribes visible text, axis titles, units, tick values,
legend entries and data labels, and summarizes what the figure shows. The description is
AI-generated: it is stored separately (data/figure_descriptions.jsonl, with model, tokens, cost)
and marked as such in the index text. Evidence for grading is always checked on the original page.
Crops go to data/crops/ (not committed; `python -m advanced.describe_figures --crops-only` rebuilds).
Re-running only describes figures that are not cached yet.
"""
import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import pymupdf as fitz
from dotenv import load_dotenv

from .ingest import DATA, PDF

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50
OUT = DATA / "figure_descriptions.jsonl"
CROPS = DATA / "crops"

PROMPT = """This image is a figure from the economics textbook "Principles of Microeconomics 3e" (OpenStax), page {page}.
Printed caption: {caption}

Write a description that will be indexed for search and used as evidence. Use only what is visible in the image; do not add outside knowledge.
1. TYPE: one of line graph, bar chart, pie chart, scatter plot, supply-demand/economic diagram, flow diagram, map, photo, table image, other.
2. TEXT: transcribe every readable title, axis label, unit, tick value, legend entry, point label and data label exactly as printed.
3. DATA: for charts, list each series with its values at labelled points or years; write "~" before any value you estimate from the axis rather than read from a label.
4. MEANING: 1-3 sentences on what the figure shows (trend, shift, comparison).
Plain text, no markdown tables, at most 350 words."""


def render(doc, unit: dict) -> bytes:
    page = doc[unit["page"] - 1]
    r = fitz.Rect(unit["image_bbox"])
    r = fitz.Rect(r.x0 - 6, r.y0 - 6, r.x1 + 6, r.y1 + 6) & page.rect
    zoom = min(150 / 72, 1400 / max(r.width, r.height))
    return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=r).tobytes("png")


def describe(client, unit: dict, png: bytes) -> dict:
    t = time.perf_counter()
    resp = client.messages.create(
        model=MODEL, max_tokens=4000, output_config={"effort": "medium"},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.standard_b64encode(png).decode()}},
            {"type": "text", "text": PROMPT.format(page=unit["page"], caption=unit["caption"] or "(none)")}]}])
    text = " ".join(b.text for b in resp.content if b.type == "text").strip()
    u = resp.usage
    return {"id": unit["id"], "model": MODEL, "stop_reason": resp.stop_reason, "description": text,
            "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
            "cost_usd": round((u.input_tokens * PRICE_IN + u.output_tokens * PRICE_OUT) / 1e6, 6),
            "elapsed_s": round(time.perf_counter() - t, 2)}


def main() -> None:
    load_dotenv(DATA.parent.parent / ".env")
    units = [json.loads(l) for l in open(DATA / "units.jsonl", encoding="utf-8")]
    figs = [u for u in units if u["type"] == "figure"]
    doc = fitz.open(PDF)
    CROPS.mkdir(exist_ok=True)
    pngs = {}
    for u in figs:
        pngs[u["id"]] = render(doc, u)
        (CROPS / f"{u['id']}.png").write_bytes(pngs[u["id"]])
    if "--crops-only" in sys.argv:
        return
    done = {}
    if OUT.exists():
        done = {json.loads(l)["id"]: 1 for l in open(OUT, encoding="utf-8")}
    todo = [u for u in figs if u["id"] not in done]
    client = anthropic.Anthropic(max_retries=5, timeout=180.0)
    total = 0.0
    with ThreadPoolExecutor(max_workers=8) as ex, open(OUT, "a", encoding="utf-8") as f:
        futs = {ex.submit(describe, client, u, pngs[u["id"]]): u for u in todo}
        for fut in futs:
            u = futs[fut]
            try:
                rec = fut.result()
            except anthropic.APIError as e:
                print("ERROR", u["id"], type(e).__name__, e)
                continue
            total += rec["cost_usd"]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if total > 3.0:
                raise SystemExit("cost cap $3 reached")
    print(f"described {len(todo)} figures, cost ${total:.4f}")


if __name__ == "__main__":
    main()
