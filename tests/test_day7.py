"""Offline checks for the Day 7 code (no DB, no API). Fakes test code paths only, never quality."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "starter"))

from src.bm25 import BM25, tokenize  # noqa: E402
from src.metrics import chunk_hits, pack_context, ranking_metrics  # noqa: E402


def chunk(cid, page, text, chapter=3):
    return {"id": cid, "text": text, "source_id": "doc", "source": "doc.pdf", "page": page,
            "metadata": {"chapter": chapter, "section": "s"}}


Q = {"evidence_groups": [[{"source_id": "doc", "page": 1, "evidence": "Price  rises “sharply”"}],
                         [{"source_id": "doc", "page": 2, "evidence": "wages fall"}]]}


class MetricTests(unittest.TestCase):
    def test_hit_uses_day6_normalization_and_page(self):
        self.assertEqual(chunk_hits(chunk("a", 1, 'The price rises "sharply" today'), Q), [0])
        self.assertEqual(chunk_hits(chunk("b", 9, 'The price rises "sharply" today'), Q), [])  # wrong page

    def test_multi_hop_needs_all_groups_for_full3(self):
        res = [chunk("a", 1, 'price rises "sharply"'), chunk("x", 5, "noise"), chunk("c", 2, "then wages fall")]
        m = ranking_metrics(res, Q)
        self.assertTrue(m["hit1"] and m["hit3"] and m["full3"])
        m = ranking_metrics(res[:2], Q)
        self.assertTrue(m["hit3"])
        self.assertFalse(m["full3"])

    def test_pack_context_never_cuts_and_dedups(self):
        res = [chunk("a", 1, "x" * 50), chunk("a", 1, "x" * 50), chunk("b", 1, "y" * 500), chunk("c", 1, "z" * 10)]
        ctx, kept = pack_context(res, budget_chars=250)
        self.assertEqual([c["id"] for c in kept], ["a", "c"])
        self.assertLessEqual(len(ctx), 250)


class BM25Tests(unittest.TestCase):
    def test_tokenize_stems_and_drops_stopwords(self):
        self.assertEqual(tokenize("The workers' wages"), ["worker", "wage"])

    def test_filter_and_ranking(self):
        idx = BM25([chunk("a", 1, "minimum wage price floor", 4), chunk("b", 1, "rent control price ceiling", 3)])
        self.assertEqual([c["id"] for c, _ in idx.search("price floor", 5)], ["a", "b"])
        self.assertEqual([c["id"] for c, _ in idx.search("price floor", 5, {"chapter": 3})], ["b"])


class FakeClient:
    """Returns scripted responses shaped like the Anthropic SDK objects used by the agent."""
    def __init__(self, scripted):
        self.scripted = iter(scripted)
        self.messages = SimpleNamespace(create=lambda **kw: next(self.scripted))


def resp(*blocks, stop="tool_use"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=10))


def tool(name, **inp):
    return SimpleNamespace(type="tool_use", name=name, input=inp, id=f"t_{name}")


class FakeRetriever:
    index = "B"
    def __init__(self): self.calls = []
    def timed_search(self, query, *, top_k, filters=None):
        self.calls.append((query, filters))
        return [dict(chunk("c1", 1, "Refunds take 7 days."), rank=1, score=0.9)], 1.0


class AgentLoopTests(unittest.TestCase):
    def make(self, scripted, max_searches=2):
        from src import agent as agent_mod
        a = agent_mod.Agent.__new__(agent_mod.Agent)
        a.name, a.cfg = "t", {"top_k": 3, "budget_chars": 4000, "max_searches": max_searches, "effort": "low"}
        a.retriever, a.client = FakeRetriever(), FakeClient(scripted)
        a.system = "s"
        return a

    def test_answer_with_valid_citation(self):
        a = self.make([resp(tool("search_textbook", query="refund")),
                       resp(tool("submit_answer", answer="7 days [c1]", citations=["c1"]))])
        out = a.run("How long?", {"chapter": 3})
        self.assertEqual(out["status"], "answered")
        self.assertEqual(a.retriever.calls, [("refund", {"chapter": 3})])  # filter comes from the session

    def test_unseen_citation_is_rejected_then_abstains(self):
        bad = tool("submit_answer", answer="7 days [zz]", citations=["zz"])
        a = self.make([resp(tool("search_textbook", query="refund")), resp(bad), resp(bad)])
        out = a.run("How long?")
        self.assertEqual(out["status"], "abstain")
        self.assertEqual(sum(e["event"] == "validation_error" for e in out["events"]), 2)

    def test_search_limit_is_enforced(self):
        a = self.make([resp(tool("search_textbook", query="a")), resp(tool("search_textbook", query="b")),
                       resp(tool("abstain", reason="none"))], max_searches=1)
        out = a.run("q")
        self.assertEqual(out["searches"], 1)
        self.assertTrue(any(e["event"] == "search_refused" for e in out["events"]))
        self.assertEqual(out["status"], "abstain")

    def test_retriever_error_is_reported_not_hidden(self):
        a = self.make([resp(tool("search_textbook", query="a")), resp(tool("abstain", reason="search failed"))])
        a.retriever.timed_search = lambda *x, **k: (_ for _ in ()).throw(ConnectionError("db down"))
        out = a.run("q")
        self.assertIn("ConnectionError", out["events"][0]["error"])


if __name__ == "__main__":
    unittest.main()
