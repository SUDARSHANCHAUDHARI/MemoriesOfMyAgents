"""
Pure-Python BM25 (Okapi BM25) — no external dependencies.
Used by search_memories.py to replace simple keyword matching.
k1=1.5, b=0.75 (standard parameters)
"""
import math
import re
from typing import Sequence


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: list[list[str]] = [_tokenize(d) for d in documents]
        self.n = len(self.corpus)
        self._build_index()

    def _build_index(self) -> None:
        dl = [len(doc) for doc in self.corpus]
        self.avgdl = sum(dl) / max(self.n, 1)
        self.dl = dl

        # term frequency per document
        self.tf: list[dict[str, int]] = []
        df: dict[str, int] = {}
        for doc in self.corpus:
            freq: dict[str, int] = {}
            for token in doc:
                freq[token] = freq.get(token, 0) + 1
            self.tf.append(freq)
            for token in freq:
                df[token] = df.get(token, 0) + 1

        # IDF (clamped to 0 — never negative)
        self.idf: dict[str, float] = {}
        for term, n_docs in df.items():
            self.idf[term] = max(0.0, math.log((self.n - n_docs + 0.5) / (n_docs + 0.5) + 1))

    def score(self, query: str, doc_idx: int) -> float:
        tokens = _tokenize(query)
        doc_tf = self.tf[doc_idx]
        doc_len = self.dl[doc_idx]
        score = 0.0
        for token in tokens:
            if token not in self.idf:
                continue
            f = doc_tf.get(token, 0)
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += self.idf[token] * numerator / (denominator + 1e-9)
        return score

    def rank(self, query: str) -> list[tuple[int, float]]:
        """Return (doc_idx, score) sorted descending."""
        scores = [(i, self.score(query, i)) for i in range(self.n)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
