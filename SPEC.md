# Grounded Catechesis Assistant — Design Spec v0.1

## Core principle
The assistant never forms or states a theological opinion or conclusion.
It retrieves relevant passages from a closed, curated corpus and presents
them, tagged by authority level, letting the user draw their own
conclusion. Any connective/explanatory text is clearly separated from
quoted material and never asserts what a passage "means" beyond the
literal text.

## Authority tiers (presented transparently, never blended silently)
1. `scripture`     — Sacred Scripture (Bible, specific translation noted)
2. `magisterium`    — Catechism, ecumenical councils, defined dogma, papal
                       encyclicals (binding/authoritative Church teaching)
3. `doctor`         — Doctors of the Church (Aquinas, Augustine, etc.) —
                       authoritative theological exposition, not dogma
4. `father`         — Church Fathers (patristic era writers)
5. `saint`          — other canonized saints' writings/reflections —
                       spiritual value, not doctrinal authority
6. `private_revelation` — Church-approved private revelation — explicitly
                       NOT binding on the faithful, always labeled as such
7. `theologian`     — approved modern commentary — lowest tier, most
                       heavily caveated, added last/optional

Every retrieved chunk carries its tier. Output is grouped/ordered by tier
(scripture + magisterium first) by default — never alphabetical or
"relevance" alone, so the user sees doctrinal weight, not just a search
score.

## Output tiers (user-selectable per query)
- **Tier 1 — Raw**: matched passages verbatim, grouped by authority tier,
  full citation. Zero connective prose. A hard post-generation filter
  rejects any output sentence that is not a verbatim extracted quote
  (same mechanism as the grounded-citations evidence gate: a "quote" is
  rejected unless it appears word-for-word in the source text).
- **Tier 2 — Organized**: same passages + minimal neutral connective
  sentences ("Source A states X. Source B adds Y.") — structural only,
  no evaluative language ("importantly," "this shows," "this proves").
- **Tier 3 — Explained**: plain-language paraphrase for each passage,
  always paired immediately with the exact verbatim quote it is based on,
  so the user can check the paraphrase against the source directly.

## Corpus — Phase 1 (public domain only, no licensing risk)
- Douay-Rheims Bible (1899 American ed., public domain)
- Catechism of the Catholic Church — full text freely published by the
  Vatican; usage reviewed before any commercial/paid tier ships
  (LICENSING NOTE below)
- Thomas Aquinas, Summa Theologiae (English Dominican Province
  translation, public domain) — tier: doctor
- Selected Church Fathers (Ante-Nicene / Nicene & Post-Nicene Fathers
  series, public domain) — tier: father

## Corpus — Phase 2 (requires licensing/permission before use)
- Modern Bible translations (RSV-CE, NAB) if preferred over Douay-Rheims
- Approved modern commentaries / theologians
- Church-approved private revelation texts (clearly tiered + labeled)

## LICENSING NOTE (must resolve before any paid/commercial launch)
The Catechism and papal documents are copyrighted (Vatican / USCCB).
Phase 1 prototype use (personal, non-commercial, small-scale) is lower
risk; reproducing the full text at scale for a paid product requires
contacting the Vatican's publishing house (Libreria Editrice Vaticana)
or USCCB for permission/licensing terms. Do not monetize before this is
resolved.

## Architecture (v0, no paid APIs required)
1. **Ingestion**: fetch source text -> chunk by natural unit (CCC
   paragraph number, Bible verse, Summa article) -> store as JSON with
   {id, text, source, citation, authority_tier, url}.
2. **Retrieval (v0)**: pure-Python keyword/TF-IDF scoring over chunks
   (no sklearn/embedding API dependency yet — deterministic and
   auditable, which fits the "no hidden interpretation" principle).
   Upgrade path: swap in embeddings later for better recall without
   changing the tiering/output logic.
3. **Tier 1 output**: fully mechanical — no LLM call needed, just
   grouped verbatim retrieval. This is the part that PROVES "zero AI
   opinion" since no generation happens at all.
4. **Tier 2/3 output**: LLM call constrained to the retrieved chunks
   only, under a strict system prompt + the verbatim-quote gate.
5. **Interface (next step)**: CLI first (this prototype), then a
   Telegram bot for real use.

## Status
- [x] Spec drafted
- [x] First 3 chunks ingested (CCC 1030-1032, 2 Mac 12:43-46, Aquinas
      Suppl. App I Q2) as proof of pipeline
- [ ] Expand corpus (full CCC, Douay-Rheims, Summa, select Fathers)
- [ ] Tier 2/3 LLM generation layer
- [ ] Telegram bot interface
- [ ] Licensing resolution for commercial launch

## Update 2026-10-29
- Full Catechism of the Catholic Church ingested: 2863 of 2865 numbered
  paragraphs (2 edge-case parsing gaps: CCC 2077, 2436 — TODO patch later).
  Source: vatican.va IntraText pages (374 pages, automated fetch+parse).
- Verified on multiple real queries (purgatory, marriage/divorce) — correct
  tiering, relevant results, honest empty-result on true gaps.
- Corpus now 2865 total chunks (2863 magisterium + 2 earlier scripture/doctor
  samples). Retrieval still <100ms in pure Python TF-IDF at this scale.
- Next: Douay-Rheims Bible (large — ~1300+ chapters, needs a prioritized
  subset or a separate multi-session batch job), more Summa, Church Fathers.
