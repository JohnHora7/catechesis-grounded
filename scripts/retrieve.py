#!/usr/bin/env python3
"""
Grounded Catechesis retrieval engine (v0 — pure stdlib, no embedding API).

Deterministic keyword/TF-IDF scoring on purpose: a transparent, auditable
retrieval method fits a product whose entire pitch is "no hidden AI
interpretation." Swap in embeddings later for better recall without
touching the tiering/output logic below.
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
                "he she we you i".split())


def tokenize(text):
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS]


def load_corpus():
    return json.loads(CORPUS_PATH.read_text())


def build_index(chunks):
    """Simple TF-IDF, pure stdlib."""
    docs_tokens = [tokenize(c["text"]) for c in chunks]
    df = Counter()
    for toks in docs_tokens:
        for w in set(toks):
            df[w] += 1
    n_docs = len(chunks)
    idf = {w: math.log((n_docs + 1) / (freq + 1)) + 1 for w, freq in df.items()}
    return docs_tokens, idf


def score(query, docs_tokens, idf):
    q_tokens = tokenize(query)
    scores = []
    for toks in docs_tokens:
        tf = Counter(toks)
        s = sum(tf.get(w, 0) * idf.get(w, 0) for w in q_tokens)
        scores.append(s)
    return scores


def search(query, min_score=0.01, top_k=10):
    chunks = load_corpus()
    docs_tokens, idf = build_index(chunks)
    scores = score(query, docs_tokens, idf)
    ranked = sorted(zip(chunks, scores), key=lambda cs: -cs[1])
    hits = [c for c, s in ranked if s >= min_score][:top_k]
    # Group/order by authority tier (doctrinal weight), not raw score
    hits.sort(key=lambda c: TIER_ORDER.index(c["authority_tier"]))
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
