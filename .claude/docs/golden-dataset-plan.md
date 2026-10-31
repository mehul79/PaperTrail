# Golden dataset plan (retrieval eval)

Status: draft, waiting on decisions in §8. Nothing is generated yet.

## 1. Purpose

One fixed set of queries with known answers, used to score every retriever variant (naive → advanced → most advanced) and the SQL/analytics path on the same footing (PRD §9). Target: ≥ 112 queries over 8 subjects (14 per subject).

## 2. What the corpus looks like (checked)

- 112 PDFs in `data/<CODE>/`, 1–4 pages each, about 250 pages in total. 7–17 papers per subject.
- Filenames: `<CODE>_<YEAR>_<E|O>_<TYPE>.pdf`, TYPE ∈ MST, EST, AUX, SUMMER (MST), SUMMER (EST). O = odd semester, E = even semester, AUX = makeup exam (confirmed by user).
- Headers print the course, date, max marks, a **faculty list**, and per-question marks and `(COx, Ly)` tags. The analytics questions depend on these fields.
- The PDFs have a text layer, but it is noisy OCR (`B.v = 28.13`, `E-EMTIT`). Gold data must be built from the **page images**, not from that text.

## 3. The key design choice: label the whole subject, write queries from 2–3 papers

Queries are written while reading 2–3 "focus" papers per subject. Their gold labels are checked against **every paper of that subject**. Two reasons:

1. Retrieval runs inside one subject (FR-19), on about 80 questions and 250 sub-parts. If only 3 papers were labeled (about 20 questions), recall@10 would be meaningless, and true matches in unlabeled papers would count as misses.
2. Counts ("how many times was LL(1) asked") are only correct if every paper was looked at.

So the work has two layers:

| Layer | File | What it is |
|---|---|---|
| Reference corpus | `eval/corpus/papers.jsonl`, `eval/corpus/questions.jsonl` | Hand-verified extraction of every paper: header fields, and each question and sub-part with marks, CO/L, page, has_table/figure, topic tags, and a short text. It is also the ground truth for the Phase 1 extraction eval. |
| Queries | `eval/golden.jsonl` | Queries whose gold answers point at reference-corpus keys. |

**Stable keys.** DB ids don't exist yet and will change on re-ingest, so gold labels use `paper_id#qnum[.sub]`, for example `UCS802_2025_O_EST#Q2c`. The eval runner maps keys to DB rows using `(paper_id, number)`.

## 4. Route classes

| Flag | Meaning | Example | Scored by |
|---|---|---|---|
| `retriever` | Content lookup with no metadata constraint | "How has SLR table construction been asked?" | recall@k, MRR, nDCG over gold keys |
| `sql` | Answerable from structured fields alone (year, exam type, marks, faculty, CO/L, counts) | "Which faculty appear on the most UCS802 papers?" / "How many 10-mark questions were in the 2025 EST?" | exact match on value or ranking |
| `hybrid` | A semantic topic combined with a metadata filter or an aggregation | "10-mark questions on LR parsing since 2025" / "How many times has deadlock come up in EST papers?" | set precision/recall, plus exact count |

Per subject (14): 6 retriever, 4 sql, 4 hybrid. Overall: about 48 / 32 / 32.

Retriever queries are split by style so we can see where each retriever wins or fails:

- `exact_term`: notation or jargon such as "SLR(1)", "Sethi-Ullman", "BCNF" (BM25 should win)
- `paraphrase`: same meaning, different words (dense retrieval should win)
- `vague`: student-speak, e.g. "parsing stuff", "that register allocation tree thing" (tests query rewriting)
- `figure_table`: the answer sits in a table or diagram (≥ 5 across the set, PRD §9)
- `negative`: the topic was never asked; the gold answer is empty (FR-31: no padding with weak matches). About 1 per subject.

Plus about 4 `cross_subject` sql queries (FR-3).

## 5. Record schema

`eval/golden.jsonl`, one object per line:

```json
{
  "id": "UCS802-H-03",
  "subject_code": "UCS802",
  "query": "10 mark questions on LR parsing from the last two years",
  "route": "hybrid",
  "style": null,
  "filters": {"marks": 10, "year_gte": 2025},
  "gold": {
    "question_keys": ["UCS802_2025_O_EST#Q3", "UCS802_2026_E_EST#Q2"],
    "partial_keys": ["UCS802_2025_E_MST#Q4b"],
    "value": null
  },
  "answer_text": "Two questions: ...",
  "has_figure_or_table": false,
  "difficulty": "medium",
  "focus_paper": "UCS802_2025_O_EST",
  "author_note": "Q4b is SLR conflict detection, related but not table construction"
}
```

- `question_keys`: fully relevant (graded 2). `partial_keys`: acceptable related matches (graded 1). Only nDCG uses the partial ones.
- `value` is set for sql and counting hybrid queries, e.g. `{"type":"count","n":3}` or `{"type":"ranking","items":["Rupali Bhardwaj","Shalini Batra"]}`. Every count also lists its `question_keys` (FR-26).
- "Now" is fixed at 2026 so that "last two years" always resolves the same way.

## 6. Build pipeline (multi-agent)

**Pass 1: reference corpus.** 8 agents run in parallel, one per subject. Each reads every page image of its subject and writes `eval/corpus/<CODE>.questions.jsonl` and `<CODE>.papers.jsonl`. Faculty names are written exactly as printed; aliases are resolved later.

Pass 1 also assigns a `repeat_group` to each sub-part. Sub-parts that ask the **same task** share a group, even when the specific grammar, schema, or numbers change. For example, "FIRST/FOLLOW + LL(1) table for grammar G" is one group across all years. Once every paper is labeled, a second agent pass per subject merges any groups that are split across agents. This becomes the gold for "most repeated questions": a ranking of groups by the number of distinct papers each appears in, plus the member keys. It is scored with pairwise precision and recall on the clusters, and an overlap check on the top 10.

**Pass 2: queries.** 8 agents run in parallel. Each picks 2–3 focus papers (different years and exam types), writes 14 queries to the quota in §4, and labels gold by searching **its subject's full reference corpus**. The query wording must not copy the question text, otherwise naive BM25 gets a free win.

**Pass 3: deterministic checks** in `eval/validate_golden.py`, a single script:
- the schema is valid, and every key resolves to a reference question
- every pure-`sql` value is **recomputed from the reference corpus** and must match, so an LLM never decides a count
- count == len(question_keys) for counting queries
- the quotas and style distribution are met, with no duplicate queries

**Pass 4: cross-review.** Each subject's queries go to a different agent that did not write them. It re-labels them blind, and any disagreement is flagged.

**Pass 5: your spot check.** You review the flagged items plus a random 15, by looking at the page images.

## 7. What comes after (not in this task)

`eval/run_retrieval.py` takes a retriever function `(subject, query, filters) -> ranked keys` and prints recall@5/10, MRR, and nDCG per route and per style. The three retriever stages plug into this runner.

## 8. Decisions needed

1. Reference-label all 112 papers (recommended), or only the 2–3 focus papers per subject?
2. Is the 6/4/4 split per subject right, or do you want more weight on retriever queries?
3. Is the faculty alias table built during Pass 1 (e.g. "Dr. R. Bhardwaj" = "Rupali Bhardwaj")?
4. Should queries include Hindi-English mixed / typo student phrasing, or English only?
