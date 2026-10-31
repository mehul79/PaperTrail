| Level | What | Ships |
|---|---|---|
| **L0** | SQL filters (unit, marks, year, exam type, faculty, topic) | Always |
| **L1** | Keyword search (BM25 via FTS5) for exact terms like `SLR(1)` | Always |
| **L2** | **Semantic search.** Embed each question and sub-part, then find the nearest ones by cosine similarity. Sub-part hits return the parent question. | **Always** |
| **L3** | **Hybrid.** L1 and L2 fused with reciprocal rank fusion, after L0 filters. This is the default search path. | **Always** |
| **L4** | Long-context baseline (the whole subject in one prompt), used as a comparator | Eval only |
| **L5** | Query rewriting | If eval shows it helps |
| **L6** | Reranker | If eval shows it helps |
| **L7** | Image/crop embeddings and crop-aware answering (option C) | If eval shows it helps on tables and figures |
