# PaperTrail

Exam paper assistant: a student enters a subject code and searches, analyzes, and practices from that subject's past exam papers (scanned PDFs from the campus portal).

- Original brief: `exam-paper-assistant-brief.md`
- Requirements: `.claude/docs/PRD.md` (read it before starting a phase; FR-numbers are referenced in code and commits)

## Status

Greenfield. No code yet. Current target: Phase 1 (one branch, one year, extraction into structured tables).

## Stack (defaults from PRD §8.2, change there first)

Python 3.12, FastAPI, SQLite + FTS5, PyMuPDF, Claude vision via the Anthropic SDK, one DB-backed worker process. No vector DB, no queue broker, no frontend framework until the corpus or load says otherwise.

## Rules that matter

- **The unit is one question**, with sub-parts, marks, and its attached table/figure. Never chunk by page or token count.
- **Analytics never use retrieval.** Counting questions go to SQL over the structured tables; the model only phrases the result.
- **Every answer cites its source**: paper, year, exam type, question number, page image link. Counts list the questions behind them.
- **Don't trust extraction silently.** Null or low-confidence fields flag the paper for review. Faculty names go through the alias table.
- **Ingestion is idempotent**, keyed on `(subject_code, paper_id)`. Re-running replaces, never duplicates. Manual overrides survive re-extraction.
- **Be polite to the portal**: rate-limited, paper lists cached. Never hammer it while testing; use downloaded fixtures.
- **Eval decides.** Rerankers, query rewriting, representation changes ship only with an eval run (`eval/`) showing they help.
- Store question crops from day one, even while answering from text (keeps the path to PRD option C additive).

## Layout (planned)

```
papertrail/      app code (ingest, extract, search, analytics, api)
eval/            eval set + runner
data/            PDFs, page images, crops, SQLite DB (gitignored)
.claude/docs/PRD.md
```
