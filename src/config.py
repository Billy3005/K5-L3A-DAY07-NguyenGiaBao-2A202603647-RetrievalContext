"""Single source of truth for paths, models, prices and experiment configurations."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Day 6 repository (corpus, pages, original benchmark). Override with DAY6_DIR.
DAY6_DIR = Path(os.environ.get("DAY6_DIR", ROOT.parent / "K5-L3A-DAY06-NguyenGiaBao-2A202603647-DataIngestion"))
DAY6_PAGES = DAY6_DIR / "starter" / "data" / "processed" / "pages.jsonl"
DAY6_QUESTIONS = DAY6_DIR / "benchmark" / "questions.jsonl"

BENCHMARK_DIR = ROOT / "benchmark"
QUESTIONS = BENCHMARK_DIR / "questions.json"
DATA_DIR = ROOT / "data" / "day6_export"
RESULTS = ROOT / "results"
SELECTION = RESULTS / "selection.json"
# Second holdout, created after the first test split was consumed (see benchmark/test2/README.md).
TEST2_DIR = BENCHMARK_DIR / "test2"
TEST2_QUESTIONS = TEST2_DIR / "questions.json"
TEST2_PREREG = RESULTS / "test2_preregistration.json"

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab")

# Day 6 embedding contract (must match the stored vectors).
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
EMBEDDING_DIM = 768
QUERY_PREFIX = "query: "

DOCUMENT_ID = "openstax-micro-3e"
INDEXES = ("B", "B500")          # Day 6 namespaces in the `chunks` table

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"

# Agent model. Prices: USD per 1M tokens, Anthropic first-party rate for prompts <= 100K tokens.
AGENT_MODEL = "claude-haiku-5-5"
PRICE_IN_PER_MTOK = 0.10
PRICE_OUT_PER_MTOK = 0.50

# Retrieval evaluation settings shared by every config (pre-registered in benchmark/README.md).
EVAL_TOP_K = 10            # ranking kept in the trace; metrics use cutoffs 1 and 3
CONTEXT_BUDGET_CHARS = 4000

# Retrieval configurations. `method` selects the pipeline; everything else is a parameter.
RETRIEVAL_CONFIGS = {
    "dense_B":         {"method": "dense",  "index": "B",
                        "hypothesis": "Baseline = Day 6 selected strategy C (dense e5 on index B + user chapter filter)."},
    "bm25_B":          {"method": "bm25",   "index": "B",
                        "hypothesis": "Lexical matching wins on exact terms ('first rule', table labels, numbers) where dense dilutes."},
    "hybrid_B":        {"method": "hybrid", "index": "B", "candidates": 50, "rrf_k": 60,
                        "hypothesis": "RRF fusion keeps dense recall on paraphrases and BM25 precision on exact terms."},
    "hybrid_rerank_B": {"method": "hybrid_rerank", "index": "B", "candidates": 50, "rrf_k": 60, "rerank_pool": 20,
                        "hypothesis": "Improvement 1: a cross-encoder reads query+chunk jointly and fixes 'right page, wrong chunk' ranking errors."},
    "hybrid_B500":     {"method": "hybrid", "index": "B500", "candidates": 50, "rrf_k": 60,
                        "hypothesis": "Improvement 2: Day 6 post-hoc B500 (<=500 chars) reduced semantic dilution; test it with hybrid."},
    "dense_B500":      {"method": "dense",  "index": "B500",
                        "hypothesis": "Diagnostic: isolates the index change (B -> B500) for dense retrieval."},
    "hybrid_rerank_B500": {"method": "hybrid_rerank", "index": "B500", "candidates": 50, "rrf_k": 60, "rerank_pool": 20,
                        "hypothesis": "Improvement 1 + 2 combined."},
}

# Agent configurations: retriever + loop/context settings. `max_searches` is a loop guard
# chosen for this corpus, not a requirement of the assignment.
AGENT_CONFIGS = {
    "agent_dense_B": {"retriever": "dense_B", "top_k": 5, "budget_chars": 4000, "max_searches": 4, "effort": "medium",
                      "hypothesis": "Baseline agent: Day 6 dense retriever behind a search tool."},
    "agent_hrr_B":   {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 4000, "max_searches": 4, "effort": "medium",
                      "hypothesis": "Retriever chosen in stage 1 (best dev Hit@3) gives the model better evidence per call."},
    "agent_hrr_B_1shot": {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 4000, "max_searches": 1, "effort": "medium",
                      "hypothesis": "Ablation: one search only (classic RAG). Tests whether multi-search helps multi-hop/paraphrase."},
    # Added after reading dev failures q22 (agent_hrr_B) and ud3 (agent_hrr_B_1shot).
    "agent_hrr_B_v2": {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 4000, "max_searches": 4,
                       "effort": "medium", "prompt": "v2", "neighbors": True,
                       "hypothesis": "Improvement 3+4: neighbor chunk for cut-off hits + rules against completing "
                                     "cut-off text and against 'not in the book' answers -> fixes q22/ud3 types."},
    "agent_hrr_B_1shot_v2": {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 4000, "max_searches": 1,
                       "effort": "medium", "prompt": "v2", "neighbors": True,
                       "hypothesis": "Same changes on the cheaper one-search agent."},
    # ---- Added AFTER the single test run (test is consumed). Evaluated on dev and on the new,
    # separately locked test2 split only (benchmark/test2/README.md). One change each vs agent_hrr_B.
    "agent_hrr_B_nbr": {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 4000, "max_searches": 4,
                        "effort": "medium", "neighbors": True,
                        "hypothesis": "Ablation of v2: neighbor chunk only (no prompt rules)."},
    "agent_hrr_B_rule": {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 4000, "max_searches": 4,
                         "effort": "medium", "prompt": "v2",
                         "hypothesis": "Ablation of v2: prompt rules only (no neighbor chunk)."},
    "agent_hrr_B_ctx8k": {"retriever": "hybrid_rerank_B", "top_k": 5, "budget_chars": 8000, "max_searches": 4,
                          "effort": "medium",
                          "hypothesis": "Test finding t09/t02: rank-5 evidence dropped by the 4000-char budget. "
                                        "8000 chars fits all top-5 B chunks (max ~1000 chars + header)."},
}
