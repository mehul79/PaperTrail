# PaperTrail

PaperTrail helps students study from past exam papers. You enter a subject code, and it lets you search that subject's old papers, see what keeps getting asked, and practice from real questions.

You could ask things like:

- Show me every question on ER diagrams.
- How many times has normalization come up?
- Which faculty set the most papers for this subject?
- Give me all the 10-mark questions from the last three years.

The papers are scanned PDFs from the campus library portal. They are noisy, with tables, diagrams and odd layouts, which makes them harder than they look.

## How it works

The core idea is that the unit is one question, not a page. Each PDF is split into questions with their sub-parts, marks, topic and any diagram, and those go into a database. Searching and counting then run against that database.

Three rules shape everything else:

- Counting questions uses SQL, never search. The model only words the result.
- Every answer shows its source: paper, year, exam type, question number and the page image.
- If extraction looks doubtful, the paper is flagged for review instead of being trusted.

## Status

Early. There is no application code yet. The first phase covers one branch and one year, turning papers into structured question data. How to read the scans is still being tested.

## Where to read more

- [CLAUDE.md](CLAUDE.md) has the stack and the working rules.
- [exam-paper-assistant-brief.md](exam-paper-assistant-brief.md) is the original idea and the reasoning behind it.
- [.claude/docs/PRD.md](.claude/docs/PRD.md) has the requirements, phase by phase.
- [.claude/docs/golden-dataset-plan.md](.claude/docs/golden-dataset-plan.md) explains how search quality will be measured.
- [notes.md](notes.md) lists the planned search levels, from plain filters up to rerankers.
- [.claude/docs/notes.md](.claude/docs/notes.md) lists the subject codes in the data folder.
