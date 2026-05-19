"""
TF-IDF cosine similarity — zero external dependencies.
Used as 4th RRF signal in search_memories.py alongside BM25.

Optional: set OPENAI_API_KEY to upgrade to text-embedding-3-small embeddings.
"""
import json
import math
import os
import re
from pathlib import Path
from typing import Optional


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# ── Local TF-IDF ─────────────────────────────────────────────────────────────

def _tf(tokens: list[str]) -> dict[str, float]:
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    n = max(len(tokens), 1)
    return {t: c / n for t, c in freq.items()}


def _idf(corpus: list[list[str]]) -> dict[str, float]:
    n = len(corpus)
    df: dict[str, int] = {}
    for doc in corpus:
        for t in set(doc):
            df[t] = df.get(t, 0) + 1
    return {t: math.log(n / max(d, 1) + 1) for t, d in df.items()}


def tfidf_vectors(documents: list[str]) -> list[dict[str, float]]:
    corpus = [_tokenize(d) for d in documents]
    idf = _idf(corpus)
    vectors = []
    for tokens in corpus:
        tf = _tf(tokens)
        vec = {t: tf[t] * idf.get(t, 0.0) for t in tf}
        vectors.append(vec)
    return vectors


def cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
    dot = sum(v1.get(t, 0.0) * v2.get(t, 0.0) for t in v2)
    n1 = math.sqrt(sum(x * x for x in v1.values()))
    n2 = math.sqrt(sum(x * x for x in v2.values()))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def tfidf_rank(query: str, documents: list[str]) -> list[tuple[int, float]]:
    """Return (doc_idx, similarity) sorted descending."""
    corpus = [_tokenize(d) for d in documents]
    idf = _idf(corpus + [_tokenize(query)])
    query_vec = {t: idf.get(t, 0.0) for t in _tokenize(query)}

    results = []
    for i, tokens in enumerate(corpus):
        tf = _tf(tokens)
        doc_vec = {t: tf[t] * idf.get(t, 0.0) for t in tf}
        sim = cosine_similarity(query_vec, doc_vec)
        results.append((i, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ── Optional: OpenAI embeddings via urllib ────────────────────────────────────

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBED_CACHE_PATH = Path.home() / ".moma" / "index" / "embed_cache.json"


def _load_cache() -> dict:
    if EMBED_CACHE_PATH.exists():
        try:
            return json.loads(EMBED_CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    EMBED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EMBED_CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache))
    tmp.replace(EMBED_CACHE_PATH)


def _embed_openai(texts: list[str]) -> Optional[list[list[float]]]:
    if not OPENAI_API_KEY:
        return None
    import urllib.request
    try:
        payload = json.dumps({"model": "text-embedding-3-small", "input": texts}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=payload,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            return [item["embedding"] for item in sorted(body["data"], key=lambda x: x["index"])]
    except Exception:
        return None


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def vector_rank(query: str, documents: list[str]) -> list[tuple[int, float]]:
    """
    Rank documents by vector similarity.
    Uses OpenAI embeddings if OPENAI_API_KEY is set, else falls back to TF-IDF.
    """
    if not OPENAI_API_KEY:
        return tfidf_rank(query, documents)

    # Check cache
    cache = _load_cache()
    import hashlib
    all_texts = [query] + documents
    keys = [hashlib.md5(t.encode()).hexdigest() for t in all_texts]
    missing_idx = [i for i, k in enumerate(keys) if k not in cache]

    if missing_idx:
        missing_texts = [all_texts[i] for i in missing_idx]
        embeddings = _embed_openai(missing_texts)
        if embeddings is None:
            return tfidf_rank(query, documents)  # fallback
        for i, emb in zip(missing_idx, embeddings):
            cache[keys[i]] = emb
        _save_cache(cache)

    query_vec = cache[keys[0]]
    qn = _norm(query_vec)

    results = []
    for doc_i in range(len(documents)):
        doc_vec = cache[keys[doc_i + 1]]
        dn = _norm(doc_vec)
        sim = _dot(query_vec, doc_vec) / (qn * dn + 1e-9)
        results.append((doc_i, sim))

    results.sort(key=lambda x: x[1], reverse=True)
    return results
