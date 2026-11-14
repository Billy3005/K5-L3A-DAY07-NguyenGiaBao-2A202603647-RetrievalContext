"""Okapi BM25 (k1=1.5, b=0.75), standard library only.

Tokenizer: NFKC + lowercase, `\\w+` tokens (so "$1,400" -> "1", "400"), a small English
stopword list and light suffix stripping (plural -s/-es/-ies, -ing, -ed). The corpus and
questions are English, so no Vietnamese word segmentation is needed.
"""
import math
import re
import unicodedata
from collections import Counter

STOPWORDS = set("""a an the and or but if of to in on at by for with from as is are was were be been being
this that these those it its into than then so such do does did what which who whom whose how why when where
there their they them he she his her we our you your i me my not no can could would should will shall may might
about over under between after before during per also any each other more most some""".split())


def stem(tok: str) -> str:
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 4 and tok.endswith("sses"):
        return tok[:-2]
    if len(tok) > 5 and tok.endswith("ing"):
        return tok[:-3]
    if len(tok) > 4 and tok.endswith("ed"):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"\w+", unicodedata.normalize("NFKC", text).lower())
    return [stem(t) for t in toks if t not in STOPWORDS]


class BM25:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks, self.k1, self.b = chunks, k1, b
        self.tfs = [Counter(tokenize(c["text"])) for c in chunks]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / len(self.lens)
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, top_k: int, filters: dict | None = None) -> list[tuple[dict, float]]:
        q = [t for t in tokenize(query) if t in self.idf]
        scored = []
        for chunk, tf, dl in zip(self.chunks, self.tfs, self.lens):
            if filters and any(chunk["metadata"].get(k) != v for k, v in filters.items()):
                continue
            s = 0.0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scored.append((chunk, s))
        scored.sort(key=lambda x: (-x[1], x[0]["id"]))
        return scored[:top_k]
