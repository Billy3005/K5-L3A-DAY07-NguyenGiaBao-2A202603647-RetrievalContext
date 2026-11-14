"""Advanced challenge, step 1: parse the whole textbook PDF into text, table and figure units.

Source: OpenStax "Principles of Microeconomics 3e" (595-page web PDF, CC BY-NC-SA 4.0).
Indexed range: PDF pages 21-576 (all chapters, appendices A-C, answer key).
Skipped (and why) is written to data/ingest_report.json.

Per page (PyMuPDF text blocks, header/footer removed):
  figure  - every raster image is matched to its "FIGURE x.y" caption (nearest caption below,
            else above); images of one caption are merged. Region bbox kept for crops/verification.
            Text = caption; a vision description is added later by describe_figures.py.
  table   - "TABLE x.y" caption + the contiguous block run directly above it. Each text block of
            the run is one row; cells (= lines of the block) are joined with " | ".
  text    - the remaining blocks in reading order, packed into ~1100-char chunks that never cross a
            page (so every citation has one page).
Output: advanced/data/units.jsonl
"""
import json
import os
import re
import sys
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PDF = Path(os.environ.get("ADV_PDF", ROOT.parent.parent / "K5-L3A-DAY06-NguyenGiaBao-2A202603647-DataIngestion"
                          / "starter" / "data" / "raw" / "principles-microeconomics-3e_-_WEB.pdf"))
FIRST, LAST = 21, 576          # 1-based PDF pages, inclusive
PRINTED_OFFSET = 12            # printed page = PDF page - 12 (checked on pages 61, 63, 72)
TEXT_TARGET = 1100
MIN_IMAGE_AREA = 3000          # pt^2; smaller images are icons

CAP_FIG = re.compile(r"^FIGURE (\d+\.\d+)")
CAP_TAB = re.compile(r"^TABLE (\d+\.\d+)")
HDR_ODD = re.compile(r"^(\d+\.\d+) • (.+?)\s+\d+$")
HDR_EVEN = re.compile(r"^\d+\s+(\d+) • (.+)$")


def clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s.replace("­", "")).strip()


def _union(rects):
    r = fitz.Rect(rects[0])
    for x in rects[1:]:
        r |= x
    return r


def _caption_run(blocks, i):
    """Caption block i plus directly following blocks at the same indent (caption continues)."""
    run = [i]
    while True:
        j = run[-1] + 1
        if j >= len(blocks):
            break
        prev, nxt = blocks[run[-1]], blocks[j]
        if abs(nxt["x0"] - blocks[i]["x0"]) < 3 and 0 <= nxt["y0"] - prev["y1"] < 5 \
                and not CAP_FIG.match(nxt["text"]) and not CAP_TAB.match(nxt["text"]):
            run.append(j)
        else:
            break
    return run


def _is_body_paragraph(b) -> bool:
    lines = [l for l in b["text"].split("\n") if l.strip()]
    avg = sum(len(l) for l in lines) / max(1, len(lines))
    return b["x0"] < 80 and (b["x1"] - b["x0"]) > 380 and avg > 60


def parse_page(page, pno: int, state: dict) -> list[dict]:
    units = []
    raw = [b for b in page.get_text("blocks") if b[6] == 0]
    blocks = []
    for b in raw:
        text = clean(b[4])
        if not text:
            continue
        if b[3] < 40:                       # running header -> chapter / section
            first = text.split("\n")[0]
            m = HDR_ODD.match(first)
            if m:
                state["section"] = f"{m.group(1)} {m.group(2).strip()}"
                state["chapter"] = int(m.group(1).split(".")[0])
            m = HDR_EVEN.match(first)
            if m:
                state["chapter"], state["chapter_title"] = int(m.group(1)), m.group(2).strip()
            continue
        if b[1] > 750 and "openstax.org" in text:
            continue
        blocks.append({"x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3], "text": text})
    blocks.sort(key=lambda b: (round(b["y0"]), b["x0"]))
    m = re.match(r"^CHAPTER (\d+)\s*\n?(.*)", blocks[0]["text"]) if blocks else None
    if m and m.group(1):
        state["chapter"] = int(m.group(1))
    for b in blocks[:3]:
        mm = re.match(r"^APPENDIX ([A-C])", b["text"])
        if mm:
            state["chapter"], state["chapter_title"], state["section"] = f"App{mm.group(1)}", b["text"].replace("\n", " "), ""
        if b["text"].startswith("ANSWER KEY"):
            state["chapter"], state["chapter_title"], state["section"] = "AnswerKey", "Answer Key", ""
    used = set()
    meta = {"chapter": state.get("chapter"), "chapter_title": state.get("chapter_title", ""),
            "section": state.get("section", ""), "printed_page": pno - PRINTED_OFFSET}

    # ---- figures
    caps = [i for i, b in enumerate(blocks) if CAP_FIG.match(b["text"])]
    imgs = []
    for x in page.get_images(full=True):
        for r in page.get_image_rects(x[0]):
            if r.get_area() >= MIN_IMAGE_AREA:
                imgs.append(r)
    groups: dict[int, list] = {}
    orphans = []
    for r in imgs:
        best, bestd = None, 1e9
        for ci in caps:
            c = blocks[ci]
            d = c["y0"] - r.y1 if c["y0"] >= r.y1 - 5 else (r.y0 - c["y1"]) + 200  # prefer caption below
            if 0 <= d < bestd and d < 400:
                best, bestd = ci, d
        (groups.setdefault(best, []) if best is not None else orphans).append(r)
    for ci, rects in groups.items():
        run = _caption_run(blocks, ci)
        used.update(run)
        caption = " ".join(blocks[k]["text"].replace("\n", " ") for k in run)
        label = CAP_FIG.match(blocks[ci]["text"]).group(1)
        region = _union(rects + [fitz.Rect(blocks[k]["x0"], blocks[k]["y0"], blocks[k]["x1"], blocks[k]["y1"]) for k in run])
        units.append({"id": f"p{pno:04d}-fig{label}", "type": "figure", "page": pno, "label": f"Figure {label}",
                      "caption": caption, "image_bbox": [round(v, 1) for v in _union(rects)],
                      "bbox": [round(v, 1) for v in region], "text": caption, **meta})
    for k, r in enumerate(orphans):
        units.append({"id": f"p{pno:04d}-img{k}", "type": "figure", "page": pno, "label": "uncaptioned image",
                      "caption": "", "image_bbox": [round(v, 1) for v in r], "bbox": [round(v, 1) for v in r],
                      "text": "", **meta})

    # ---- tables
    for ci, b in enumerate(blocks):
        m = CAP_TAB.match(b["text"])
        if not m or ci in used:
            continue
        run = _caption_run(blocks, ci)
        # grow the region upward from the caption: a block joins when it ends within 28pt of the
        # current region top (or overlaps it vertically, e.g. a label column beside a long cell)
        cands = sorted((k for k in range(ci) if k not in used), key=lambda k: -blocks[k]["y1"])
        rows, top = [], b["y0"]
        for k in cands:
            cand = blocks[k]
            if top - cand["y1"] > 28:
                break
            if _is_body_paragraph(cand) or CAP_FIG.match(cand["text"]) or CAP_TAB.match(cand["text"]):
                if cand["y1"] <= top:
                    break
                continue
            rows.append(k)
            top = min(top, cand["y0"])
        rows.sort(key=lambda k: (round(blocks[k]["y0"]), blocks[k]["x0"]))
        used.update(run + rows)
        caption = " ".join(blocks[k]["text"].replace("\n", " ") for k in run)
        body = "\n".join(" | ".join(l.strip() for l in blocks[k]["text"].split("\n") if l.strip()) for k in rows)
        region = _union([fitz.Rect(blocks[k]["x0"], blocks[k]["y0"], blocks[k]["x1"], blocks[k]["y1"]) for k in rows + run])
        units.append({"id": f"p{pno:04d}-tab{m.group(1)}", "type": "table", "page": pno,
                      "label": f"Table {m.group(1)}", "caption": caption, "n_rows": len(rows),
                      "bbox": [round(v, 1) for v in region], "text": f"{caption}\n{body}", **meta})

    # ---- text
    buf, n, bboxes = [], 0, []

    def flush():
        nonlocal buf, n, bboxes
        if buf:
            units.append({"id": f"p{pno:04d}-t{n}", "type": "text", "page": pno, "label": "", "caption": "",
                          "bbox": [round(v, 1) for v in _union(bboxes)], "text": "\n".join(buf), **meta})
            n += 1
        buf, bboxes = [], []

    for i, b in enumerate(blocks):
        if i in used:
            continue
        t = b["text"].replace("\n", " ")
        pieces = [t] if len(t) <= TEXT_TARGET * 1.4 else re.split(r"(?<=[.!?])\s+(?=[A-Z])", t)
        for piece in pieces:
            if buf and sum(len(x) for x in buf) + len(piece) > TEXT_TARGET:
                flush()
            buf.append(piece)
            bboxes.append(fitz.Rect(b["x0"], b["y0"], b["x1"], b["y1"]))
    flush()
    return units


def main() -> None:
    doc = fitz.open(PDF)
    DATA.mkdir(exist_ok=True)
    state: dict = {"chapter": 1, "chapter_title": "Welcome to Economics!", "section": ""}
    units = []
    for pno in range(FIRST, LAST + 1):
        units.extend(parse_page(doc[pno - 1], pno, state))
    with open(DATA / "units.jsonl", "w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    by = {}
    for u in units:
        by[u["type"]] = by.get(u["type"], 0) + 1
    report = {
        "pdf": PDF.name, "pdf_pages": doc.page_count, "indexed_pages": [FIRST, LAST],
        "skipped": {"1-20": "cover, copyright, table of contents, preface (no subject content)",
                    "577-595": "references list and alphabetical index (bibliographic / navigational only)"},
        "units": by, "uncaptioned_images": sum(1 for u in units if u["label"] == "uncaptioned image"),
        "tables_without_rows": [u["id"] for u in units if u["type"] == "table" and u["n_rows"] == 0],
        "pages_without_units": [p for p in range(FIRST, LAST + 1) if not any(u["page"] == p for u in units)],
    }
    (DATA / "ingest_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
