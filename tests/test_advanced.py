"""Offline checks for the advanced pipeline (no PDF, no API, no models). Code paths only, never quality."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_day7 import FakeClient, resp, tool  # noqa: E402


def unit(uid, typ="table", text="TABLE 1.1 x\n$1 | 2"):
    return {"id": uid, "type": typ, "label": "Table 1.1", "page": 10, "printed_page": -2, "chapter": 1,
            "section": "s", "bbox": [0, 0, 10, 10], "index_text": text, "rank": 1, "score": 1.0}


class FakeSearcher:
    def __init__(self):
        self.calls = []

    def search(self, query, top_k, ftype=None):
        self.calls.append((query, ftype))
        return [unit("p0010-tab1.1")]


class AdvancedAgentTests(unittest.TestCase):
    def make(self, scripted, max_views=2):
        from advanced import agent as m
        m.render_region = lambda u: b"\x89PNG fake"          # no PDF needed
        a = m.Agent.__new__(m.Agent)
        a.name = "t"
        a.cfg = {"view": True, "top_k": 3, "budget_chars": 4000, "max_searches": 2, "max_views": max_views, "effort": "low"}
        a.searcher, a.client, a.system, a.tools = FakeSearcher(), FakeClient(scripted), "s", m.TOOLS_BASE
        return a

    def test_view_requires_a_searched_unit_and_returns_an_image(self):
        a = self.make([resp(tool("view_region", unit_id="p0010-tab1.1")),          # not searched yet -> refused
                       resp(tool("search_document", query="q", content_type="table")),
                       resp(tool("view_region", unit_id="p0010-tab1.1")),
                       resp(tool("submit_answer", answer="2 [p0010-tab1.1]", citations=["p0010-tab1.1"]))])
        out = a.run("q")
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["views"], 1)
        self.assertEqual([e["event"] for e in out["events"] if "view" in e["event"]], ["view_refused", "view"])
        self.assertEqual(a.searcher.calls, [("q", "table")])

    def test_any_means_no_type_filter_and_view_limit_enforced(self):
        a = self.make([resp(tool("search_document", query="q", content_type="any")),
                       resp(tool("view_region", unit_id="p0010-tab1.1")),
                       resp(tool("view_region", unit_id="p0010-tab1.1")),
                       resp(tool("abstain", reason="x"))], max_views=1)
        out = a.run("q")
        self.assertEqual(a.searcher.calls, [("q", None)])
        self.assertEqual(out["views"], 1)
        self.assertEqual(out["status"], "abstain")

    def test_pack_caps_one_long_unit(self):
        from advanced.agent import pack
        ctx, kept = pack([unit("a", text="x" * 10000), unit("b", text="short")], 4000)
        self.assertEqual([k["id"] for k in kept], ["a", "b"])
        self.assertIn("truncated", ctx)
        self.assertLessEqual(len(ctx), 4000)


class IngestHelperTests(unittest.TestCase):
    def test_body_paragraph_vs_table_cell(self):
        from advanced.ingest import _is_body_paragraph
        para = {"x0": 72, "x1": 540, "text": "A long sentence of body text that runs across the full width of the page."}
        cell = {"x0": 181, "x1": 280, "text": "$1.00\n800"}
        self.assertTrue(_is_body_paragraph(para))
        self.assertFalse(_is_body_paragraph(cell))

    def test_caption_run_joins_continuation_lines_only(self):
        from advanced.ingest import _caption_run
        b = [{"x0": 72, "y0": 478, "y1": 490, "text": "FIGURE 3.3 A Supply Curve"},
             {"x0": 72, "y0": 492, "y1": 531, "text": "at each price ..."},
             {"x0": 185, "y0": 550, "y1": 562, "text": "Price (per gallon)"}]
        self.assertEqual(_caption_run(b, 0), [0, 1])


if __name__ == "__main__":
    unittest.main()
