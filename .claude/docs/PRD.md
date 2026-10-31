# PaperTrail: Product Requirements Document

| | |
|---|---|
| Status | Draft v0.1 |
| Date | 2026-10-25 |
| Owner | Mehul Gupta |
| Source | `exam-paper-assistant-brief.md` |

---

## 1. Summary

PaperTrail lets a student type a subject code and then work with that subject's past exam papers: search questions by topic, see which questions repeat, see which faculty set which papers, and ask things like "show me all 10-mark questions on LR parsing from the last three years."

Papers come from the campus portal, which lists them per subject code. They are scanned PDFs with noisy OCR, math and grammar notation, tables, diagrams, and code. Getting that data into a correct, queryable shape is most of the work. Search and chat are the easy part once it is.

## 2. Problem

Students preparing for exams want to know what gets asked, how often, and in what form. Today they download PDFs one at a time from the portal and skim them by hand. That is slow, and it can't answer questions like "how many times has ambiguity come up?" or "which faculty sets Compiler Design most often?"

A generic chatbot over the PDFs doesn't solve it either:

- Plain OCR corrupts notation (`E.val` came out as "E. vat"), and nothing flags the error.
- Top-k retrieval can't count, so frequency questions get arbitrary answers.
- Page-level search returns whole pages when the student wants one question.

## 3. Goals and non-goals

### Goals

1. **Correct question-level data.** Every question in an ingested paper is stored once, with its sub-parts, marks, any attached table or figure, and metadata (course, year, exam type, faculty, question number, page).
2. **Three query types answered by the right machinery:** semantic search, analytics (counting), and browse/practice (filter and list).
3. **Answers anyone can check.** Every answer cites paper, year, and question number, and links to the original page image.
4. **On-demand ingestion.** A subject is processed the first time someone asks for it, without duplicate work.
5. **Measured quality.** An eval set decides design choices, not guesses.

### Non-goals (v1)

- Solving questions or writing model answers.
- Accounts, social features, or sharing.
- Indexing every subject up front.
- Mobile apps. A responsive web page is enough.
- Supporting other universities' portals.

## 4. Users

| User | Need |
|---|---|
| Student before an exam | "What's important in this subject?" Topic frequency, repeated questions, unit-wise lists. |
| Student practicing | All past questions for a unit, or a mock paper built from them. |
| Student looking something up | "How was SLR table construction asked?" Exact past wording with the original page. |
| Maintainer (us) | See ingestion status, review low-confidence extractions, fix bad records. |

## 5. User stories

1. As a student, I enter a subject code and immediately see whether it's indexed, which years and exam types are covered, and how many papers.
2. As a student, if the subject isn't indexed, I see "Preparing this subject" with progress, and the page updates when it's ready.
3. As a student, I search "error recovery" and get matching questions, each with paper, year, question number, marks, and a link to the page image.
4. As a student, I search the exact term "SLR(1)" and get questions containing that term, not loosely related ones.
5. As a student, I ask "how many times was ambiguity asked?" and get a count plus the list of questions behind it.
6. As a student, I ask "which faculty appears most for Compiler Design?" and get a ranked list where "Rupali Bhardwaj" and "Dr. R. Bhardwaj" count as one person.
7. As a student, I filter by unit, marks, year range, or exam type and see the matching questions.
8. As a student, I generate a mock paper from past questions matching a typical paper's structure.
9. As a student, for a question with a table or diagram, I see the cropped original image next to the text.
10. As a maintainer, I upload PDFs by hand when the portal is down or blocks automation.
11. As a maintainer, I see a review queue of papers with null or low-confidence fields and can correct them.

## 6. Functional requirements

### 6.1 Subject entry and coverage

- **FR-1** Accept a subject code. Normalize case and whitespace.
- **FR-2** Show coverage for the subject: years, exam types, paper count, last refreshed time.
- **FR-3** Show a global list of indexed subjects. Any cross-subject analytics must say they cover only indexed subjects.

### 6.2 Ingestion

- **FR-4** If a subject isn't indexed, enqueue a background job and return a status the UI can poll.
- **FR-5** Jobs are idempotent, keyed on `(subject_code, paper_id)`. Concurrent requests for the same subject attach to the existing job.
- **FR-6** Cache the portal's paper list per subject. Re-check it on a schedule (default: weekly), not per query.
- **FR-7** Rate-limit portal requests (default: 1 request every 2 seconds, one concurrent connection).
- **FR-8** Manual upload: accept PDFs plus subject code, year, and exam type, and run them through the same pipeline.
- **FR-9** Keep the original PDF and rendered page images so answers can link to them.
- **FR-10** A failed paper doesn't fail the subject. It is marked failed with the error, and the rest proceed.

### 6.3 Extraction

The pipeline, per paper:

1. Render each page to an image (fixed DPI, default 200).
2. Read the paper header once: course code, course name, year, exam type, faculty, max marks, date.
3. Detect question boundaries and crop each question's region, including attached tables and figures. A question that spans pages is stitched together.
4. Transcribe each question with a vision model: text as text, tables as markdown, math as LaTeX, code as code blocks, diagrams as a short description.
5. Extract per-question fields: question number, sub-parts, marks, unit (if printed), CO/BL tags (if printed).
6. Generate topic tags and a canonical question form, used to match repeats across years.
7. Record a confidence score per field.

Requirements:

- **FR-11** The unit of storage is one question with all sub-parts. Long multi-part questions also get sub-part records linked to the parent.
- **FR-12** Every question record carries: course, year, exam type, faculty, question number, marks, page reference, crop image path.
- **FR-13** Faculty names are normalized to a canonical person through an alias table. Unknown variants go to the review queue rather than creating a new person silently.
- **FR-14** Any field that is null or below the confidence threshold flags the paper for review.
- **FR-15** Re-running extraction on a paper replaces its records; it never duplicates them.

### 6.4 Query routing

- **FR-16** Classify each query as `semantic`, `analytical`, or `browse`, and extract filters (subject, years, marks, unit, exam type, faculty).
- **FR-17** Explicit UI filters override router-extracted filters.
- **FR-18** Log every routing decision with the query, so misroutes can be added to the eval set.

### 6.5 Semantic search

- **FR-19** Apply metadata filters first, then search within the filtered set.
- **FR-20** Hybrid retrieval: keyword (BM25) plus dense embeddings over question text, fused by reciprocal rank fusion.
- **FR-21** Retrieve on sub-part records, return the parent question.
- **FR-22** Optional query rewriting into syllabus vocabulary ("parsing stuff" → "LR, LL, shift-reduce"). Kept only if the eval set shows it helps.
- **FR-23** Optional reranking. Kept only if the eval set shows it helps at this corpus size.

### 6.6 Analytics

- **FR-24** Analytical queries never go through retrieval. They run against the structured tables (SQL), and the model only phrases the result.
- **FR-25** Supported questions at minimum: topic frequency, repeated questions (by canonical form), faculty frequency, marks distribution per topic or unit, questions per year.
- **FR-26** Every count is shown with the list of questions or papers it came from.

### 6.7 Browse and practice

- **FR-27** Filter-and-list over metadata: by unit, marks, year range, exam type, faculty, topic tag.
- **FR-28** Mock paper: pick past questions matching the typical structure of that subject's papers (section count, marks per section), avoiding repeats within one mock. Show the source of each picked question.

### 6.8 Answering

- **FR-29** Every returned question shows paper, year, exam type, question number, marks, and a link to the page image.
- **FR-30** For questions with figures or tables, the answering model receives the cropped image, not only the transcription.
- **FR-31** If nothing matches, say so. Don't pad with weak matches.

### 6.9 Review and admin

- **FR-32** A review queue lists flagged papers and questions with the original crop beside the extracted fields.
- **FR-33** Corrections are saved and survive re-extraction (manual overrides win).

## 7. Data model (first cut)

```
subjects(code PK, name, branch, indexed_at, paper_list_checked_at)
papers(id PK, subject_code FK, year, exam_type, date, max_marks,
       source_url, pdf_path, status, error, needs_review)
faculty(id PK, canonical_name)
faculty_aliases(alias PK, faculty_id FK)
paper_faculty(paper_id FK, faculty_id FK)
pages(paper_id FK, page_no, image_path)
questions(id PK, paper_id FK, parent_id FK NULL, number, text,
          figure_description, marks, unit, page_no, crop_path,
          canonical_form, confidence, manual_override)
question_topics(question_id FK, topic)
question_embeddings(question_id FK, model, vector)
jobs(id PK, subject_code, paper_id NULL, kind, status, attempts,
     error, created_at, updated_at, UNIQUE(subject_code, paper_id, kind))
query_log(id PK, query, route, filters, latency_ms, result_ids, feedback, created_at)
```

## 8. Technical approach

### 8.1 Representation (brief §5)

Ship **option B** (transcribe everything to text) first, while storing question crops from day one. That makes moving to **option C** (dual representation: text plus crop, crop passed at answer time, optional image embedding) additive. Option A (vision-only page retrieval) is built only as a comparison point on the eval set, since it can't support analytics or exact-term search.

### 8.2 Default stack

Chosen to keep the moving parts few at this corpus size (one subject is tens of papers, a few hundred questions). Each is open to change before Phase 1 starts.

| Concern | Default | Why |
|---|---|---|
| Language | Python 3.12 | PDF and ML tooling |
| API | FastAPI | Small, async, typed |
| Store | SQLite with FTS5 | Structured tables, keyword search, and job state in one file |
| Dense vectors | Stored in SQLite, brute-force cosine | A few thousand vectors don't need a vector DB |
| PDF rendering | PyMuPDF | Fast page-to-image |
| Transcription, extraction, routing, answering | Claude (vision) via Anthropic SDK | One provider for vision and text |
| Embeddings | Decided in Phase 2 by eval | |
| Background jobs | DB-backed job table + one worker process | Idempotency comes from the unique key; no broker needed |
| Frontend | Server-rendered HTML + small JS | Search box, filters, results, status polling |

Upgrade paths: Postgres + pgvector if multiple workers or concurrent writes become a problem; a real queue if one worker can't keep up.

### 8.3 Long-context baseline

For one subject, the full set of transcribed papers likely fits in one long-context call. This is the baseline for semantic and browse queries. Retrieval stays only if it beats the baseline on accuracy or cost per query.

## 9. Evaluation

- **Eval set:** 40 to 50 questions with known answers, covering all three query types, plus at least 5 table and diagram cases. Stored in the repo as data (`eval/`).
- **Metrics, reported separately:**
  - retrieval hit rate (recall@k for the gold question IDs)
  - answer correctness
  - aggregation accuracy (exact match on counts and rankings)
  - routing accuracy
  - extraction quality: sample papers and check faculty, date, marks, and question boundaries against the originals
- **Rule:** no pipeline change (reranker, rewriter, representation switch) ships without an eval run showing it helps.
- Extraction errors break analytics silently, so null and low-confidence fields are logged and reviewed by hand (FR-14).

## 10. Success metrics

| Metric | Target for v1 |
|---|---|
| Question boundary accuracy on sampled papers | ≥ 95% |
| Header field accuracy (faculty, year, exam type) | ≥ 98% after review |
| Retrieval hit rate @10 on semantic eval | ≥ 90% |
| Aggregation accuracy on analytical eval | 100% on indexed data |
| Routing accuracy | ≥ 95% |
| p50 latency, search / analytics | < 3 s |
| Time to index a new subject | < 15 min for ~20 papers |

These are starting targets. Revise them after Phase 2 once the baseline is known.

## 11. Phasing

| Phase | Scope | Exit criteria |
|---|---|---|
| 1 | One branch, one year, ingested up front. Rendering, transcription, extraction, structured tables populated. Review queue. | Extraction quality checked on sampled papers; faculty aliases resolved. |
| 2 | Hybrid retrieval over questions. Eval set built. Long-context baseline. | Retrieval hit rate measured against baseline. |
| 3 | Query router and analytics path. | Routing and aggregation accuracy measured. |
| 4 | Tables and figures: compare A, B, C on the eval set. | Representation chosen by numbers. |
| 5 | On-demand ingestion with job status in the UI. Portal scraping with rate limit and caching. Manual upload. | New subject indexes end to end with no manual steps. |
| 6 | Real students. Usage and feedback logging. | Feedback loop feeding new eval cases. |

## 12. Non-functional requirements

- **Politeness:** respect the portal's rate limit (FR-7) and robots rules; identify the client in the User-Agent.
- **Reliability:** jobs retry with backoff (max 3 attempts); a crashed worker leaves jobs resumable.
- **Cost:** log model tokens per paper ingested and per query. Cache transcriptions so re-running extraction doesn't re-pay for vision calls unless asked.
- **Privacy:** no student accounts in v1. Query logs store no personal data.
- **Access:** if papers may not be exposed outside the campus network, the deployment must sit behind campus network or SSO (see open question 1).

## 13. Risks

| Risk | Mitigation |
|---|---|
| Transcription errors in notation | Vision model instead of plain OCR; crop passed at answer time; review queue. |
| Inconsistent headers across years | Per-field confidence; manual override; alias table for faculty. |
| Portal blocks scraping or is unstable | Cached paper lists, rate limit, manual upload fallback. |
| Analytics wrong because data is incomplete | UI states coverage explicitly; counts list their sources. |
| Model cost during ingestion | Cache transcriptions; ingest on demand, not everything. |
| Not allowed to expose papers publicly | Resolve open question 1 before Phase 6. |

## 14. Open questions

1. Are we allowed to index and expose the papers outside the campus network?
2. How consistent are headers across years? This decides how hard extraction is.
3. Practice features (mock papers, topic weightage) in v1, or search only? This PRD assumes mock papers are in scope (FR-28) but can be cut.
4. Is the portal stable enough to scrape politely, or is manual upload the main path?
5. Which branch and year go first in Phase 1?
6. Where is the syllabus (units, topics) available, for topic tags and query rewriting?
