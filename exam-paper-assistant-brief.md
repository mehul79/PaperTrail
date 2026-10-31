# Exam Paper Assistant: Project Brief

## 1. What it is

A tool where a student enters a subject code and can then explore that subject's past exam papers: find questions by topic, see what gets repeated, see which faculty set what, and ask things like "show me all 10-mark questions on LR parsing from the last three years." The papers come from the campus portal, which lists them per subject code.

The data is real, messy, and useful to actual users. That is the main point of the project.

## 2. What users will ask

Queries fall into three types, and each needs different machinery.

- **Semantic questions:** "questions on error recovery", "how was SLR table construction asked?" These go to retrieval.
- **Analytical questions:** "which faculty appears most for Compiler Design", "how many times was ambiguity asked?" These need counting over structured data. Top-k retrieval can't count, so the answer would be wrong or arbitrary.
- **Browse and practice:** "give me all questions for unit 3", "make a mock paper from past questions." These are filter-and-list operations over metadata.

A router that sends each query down the right path is part of the project.

## 3. What the data looks like

Scanned PDFs with noisy OCR, inconsistent headers, math and grammar notation, tables, flow diagrams, code listings, and sometimes handwritten marks. For example, plain OCR turned `E.val` into "E. vat" in a Compiler Design paper. A text-only OCR pipeline quietly corrupts a lot of this, and the corruption stays invisible until a student gets a wrong answer.

## 4. Ingestion: on demand, per subject

Instead of indexing everything up front, ingest a subject the first time someone asks for it.

1. Student enters a subject code. If it is already indexed, go straight to search.
2. If not, a background job fetches that subject's paper list, processes each paper, and writes everything to the store. The student sees a status message ("preparing this subject").
3. Jobs are idempotent and keyed on subject plus paper ID, so simultaneous requests don't duplicate work.

Start with one year and one branch ingested up front, so you can build the eval set and find failure modes before adding lazy loading. Be explicit in the UI about which subjects are indexed, because cross-subject analytics are only valid over what is loaded.

Practical notes:

- Cache the portal's paper list and re-check it occasionally, not on every query.
- Rate-limit any scraping so the campus server isn't hammered.
- Keep a manual upload fallback in case the portal is unstable or blocks automation.

## 5. Tables and images

The simple option is to embed page images with a vision retrieval model (the ColPali family) and skip parsing entirely. These models represent a page as a grid of patch vectors and match queries against them, so tables, diagrams, and odd layouts work without any extraction step. It is a legitimate simplification, and for papers with figures it earns its place.

But on its own it has gaps:

- **Exact matching.** Queries like "SLR(1)" or "Thompson's construction" are exact-term lookups. Keyword search handles these better than embeddings, and image embeddings give you no text to keyword-search.
- **Structured extraction.** Faculty, date, marks, and course code have to be read out as fields. Embeddings can't be counted or filtered.
- **Granularity.** Page-level embeddings retrieve a whole page, but the unit of meaning is a single question, and one page often holds several.
- **Storage.** Multi-vector page embeddings are much larger than text vectors. Manageable at this corpus size, but not free.

### Three options

**A. Vision-only.** Embed page images, retrieve pages, hand the page image to a vision-capable model to answer. Simplest to build. Weak on exact terms, no analytics, coarse results.

**B. Transcribe everything to text.** A vision model reads each question and outputs text: tables as markdown, math as LaTeX, diagrams as a written description. Then it is a normal text pipeline. Cleanest for search and analytics, but it depends on transcription quality, and diagram descriptions lose detail.

**C. Dual representation (recommended).** Detect each question's region on the page and crop it, so a table or figure travels with its question. For each crop, store:

- the transcription
- a short description of any figure or table
- the extracted metadata
- optionally, an image embedding

Search runs over the text side, with the image embedding as a second signal for figure-heavy questions. At answer time, pass the cropped image itself to the model, not just the transcription, so a lossy description can't cause wrong answers.

For a fast first version, start with A or B and let the eval set show where it fails. Moving to C later is mostly additive.

## 6. Chunking

The unit is one question, with all its sub-parts, its marks, and any attached table or figure.

- For long multi-part questions, also store sub-part chunks linked to the parent. Retrieve on the small piece, return the whole question.
- Attach metadata to every chunk: course, year, exam type, faculty, question number, marks, page reference.
- Generate topic tags per question, and optionally a normalized "canonical question" form so repeated questions across years can be recognized.
- Normalize faculty names ("Rupali Bhardwaj" vs "Dr. R. Bhardwaj"), or the counts will split.

## 7. Retrieval pipeline options

There is no single right answer here, and the corpus is small enough to compare several.

- **Keyword plus dense hybrid**, fused by rank. A solid default.
- **Metadata filtering before search.** Cheap and often the biggest quality gain, since many queries are really filters.
- **Reranking** the top candidates with a stronger model. Worth testing, but measure whether it helps at this scale.
- **Query rewriting.** Expand a student's vague phrasing into syllabus vocabulary ("parsing stuff" becomes "LR, LL, shift-reduce").
- **Late-interaction or multi-vector retrieval** over the visual side, if you take option C.
- **Long-context baseline.** For one subject, the whole set of papers may fit in a long-context model. Use it as a baseline. Retrieval only justifies itself if it beats this on cost or accuracy.

For analytical queries, skip retrieval entirely: query the structured table directly, then let the model phrase the result.

## 8. Answering

Return the matching questions with their source (paper, year, question number) and a link to the original page image. For synthesized answers (topic frequency, repeated questions), show the counts and the papers they came from so the student can check. For figure questions, give the model the cropped image.

## 9. Evaluation

Build a set of 40 to 50 questions with known answers, covering all three query types, plus a handful of table and diagram cases. Measure these separately:

- retrieval hit rate
- answer correctness
- aggregation accuracy
- extraction quality (sample papers and check extracted faculty, dates, and question boundaries against the originals)

Extraction errors silently break the analytics, so log papers where a field came out null or low-confidence and review them by hand.

## 10. Phasing

1. One branch, one year. Transcription and extraction working, structured table populated.
2. Retrieval over questions, with the eval set and a baseline.
3. Query router and the analytics path.
4. Table and figure handling, comparing A, B, and C on the eval set.
5. On-demand ingestion for new subjects, with job status in the UI.
6. Real students using it, with usage and feedback logged.

## 11. Open questions

- Are you allowed to index and expose the papers outside the campus network?
- How consistent are the headers across years? That decides how hard extraction is.
- Do you want practice features (mock papers, topic weightage) or only search?
- Is the portal stable enough to scrape politely, or do you need a manual upload fallback?
