#!/usr/bin/env python3
"""
Grounded Catechesis retrieval engine (v0.3 — pure stdlib, BM25).

History of fixes found in testing (kept here so no one "fixes" it back):
- v0.1: raw TF-IDF term-frequency sums. Bug: favored LONG documents — a
  Catechism paragraph discussing a commandment outscored (35x) the actual
  one-sentence Bible verse stating it, silently burying Scripture under
  commentary on it.
- v0.2: switched to cosine-normalized TF-IDF + per-tier top-k. Overcorrected:
  cosine normalization over-rewards very SHORT documents with a single
  incidental keyword match (e.g. "let the dead bury their dead" outscored
  genuine purgatory passages on a "prayer for the dead" query, just because
  it's short and contains "dead").
- v0.3 (current): BM25 — saturating term frequency + tunable length
  normalization (k1=1.5, b=0.75, the standard defaults). This is the actual
  standard solution to exactly this long-vs-short tradeoff (same algorithm
  Elasticsearch/Lucene use for keyword search). Verified against all three
  known problem queries before shipping (see project notes).

Per-tier retrieval is kept regardless of scoring method: each authority
tier is ranked and cut independently, so no tier's volume can crowd out
another's best matches.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

CORPUS_PATH = Path(__file__).parent.parent / "corpus" / "chunks.json"

TIER_ORDER = ["scripture", "magisterium", "doctor", "father", "saint",
              "private_revelation", "theologian"]
TIER_LABELS = {
    "scripture": "Sacred Scripture",
    "magisterium": "Magisterial Teaching (binding)",
    "doctor": "Doctor of the Church (authoritative, not dogma)",
    "father": "Church Father (patristic era)",
    "saint": "Saint's writing (spiritual value, not doctrinal authority)",
    "private_revelation": "Approved Private Revelation (NOT binding on the faithful)",
    "theologian": "Theological commentary (lowest authority, most caveated)",
}

STOPWORDS = set("a an the of to in is are was were be been being and or "
                "but if on at by for with from this that these those as "
                "it its into about what does do did their his her they "
                "he she we you i shall thou thy".split())

BM25_K1 = 1.5
BM25_B = 0.75


def tokenize(text):
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS]


def load_corpus():
    return json.loads(CORPUS_PATH.read_text())


def build_index(chunks):
    docs_tokens = [tokenize(c["text"]) for c in chunks]
    doc_len = [len(t) for t in docs_tokens]
    avgdl = sum(doc_len) / len(doc_len) if doc_len else 1.0

    df = Counter()
    for toks in docs_tokens:
        for w in set(toks):
            df[w] += 1
    n_docs = len(chunks)
    # BM25 idf (standard formulation, floored at a small positive value)
    idf = {w: max(0.01, math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1))
           for w, freq in df.items()}

    doc_tfs = [Counter(toks) for toks in docs_tokens]
    return doc_tfs, doc_len, avgdl, idf


def score(query, doc_tfs, doc_len, avgdl, idf):
    q_tokens = set(tokenize(query))
    scores = []
    for tf, dl in zip(doc_tfs, doc_len):
        s = 0.0
        for w in q_tokens:
            f = tf.get(w, 0)
            if f == 0:
                continue
            num = f * (BM25_K1 + 1)
            den = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl)
            s += idf.get(w, 0) * (num / den)
        scores.append(s)
    return scores


def search(query, min_score=0.5, per_tier_k=5):
    """Per-tier retrieval: rank within each authority tier independently
    so no single tier's volume can crowd out another's best matches."""
    chunks = load_corpus()
    doc_tfs, doc_len, avgdl, idf = build_index(chunks)
    scores = score(query, doc_tfs, doc_len, avgdl, idf)

    by_tier = {t: [] for t in TIER_ORDER}
    for c, s in zip(chunks, scores):
        if s >= min_score:
            by_tier[c["authority_tier"]].append((c, s))

    hits = []
    for tier in TIER_ORDER:
        ranked = sorted(by_tier[tier], key=lambda cs: -cs[1])[:per_tier_k]
        hits.extend(c for c, s in ranked)
    return hits


def render_tier1(hits):
    """Raw mode: verbatim passages grouped by authority tier. No synthesis."""
    if not hits:
        return "No passages in the corpus matched this query."
    out = []
    current_tier = None
    for h in hits:
        if h["authority_tier"] != current_tier:
            current_tier = h["authority_tier"]
            out.append(f"\n=== {TIER_LABELS[current_tier]} ===\n")
        out.append(f'"{h["text"]}"\n  — {h["source"]}, {h["citation"]}\n')
    return "\n".join(out)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "purgatory prayer for the dead"
    hits = search(query)
    print(f"Query: {query}\n")
    print(render_tier1(hits))
