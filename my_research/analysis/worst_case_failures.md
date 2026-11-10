# 💥 WORST-CASE FAILURE CATALOG: WHY EXISTING TABLE RAG BREAKS

This document catalogs the exact edge-case scenarios found in SEC 10-K/10-Q filings that cause standard RAG pipelines, semantic splitters, and naive LLM table extractors to crash, hallucinate, or lose critical numbers.

---

### Failure 1: Multi-Tiered (Hierarchical) Column Super-Headers

#### Real SEC 10-K Pattern:
In real annual reports, columns are grouped under multi-level headers:

```text
| Metric | Three Months Ended Sept 30, | Nine Months Ended Sept 30, |
|        |      2026   |    2025      |     2026     |    2025     |
| :---   |    :---:    |   :---:      |    :---:     |   :---:     |
| Net Sales | $24,150  | $21,300      |   $74,800    |  $68,200    |
```

#### Why Existing Systems Crash:
- **Naive Markdown Splitters:** Treat Row 1 as the header and Row 2 as data, completely losing the connection between `2026` and `Three Months` vs. `Nine Months`.
- **Query:** *"What were Net Sales for the nine-month period ended Sept 30, 2026?"*
- **Failure:** The retriever returns `$24,150` (Three Months) because it matches `Sept 30, 2026` and cannot disambiguate the super-header span.

---

### Failure 2: Parenthetical Negative Financial Values

#### Real SEC 10-K Pattern:
GAAP financial conventions express negative numbers with parentheses:
```text
| Cash Flows from Operating Activities | $4,850  |
| Capital Expenditures                 | (1,240) |
| Free Cash Flow                       | $3,610  |
```

#### Why Existing Systems Crash:
- Many NLP tokenizers and regex extractors strip parentheses or tokenize `(1,240)` as `["(", "1", ",", "240", ")"]`.
- When linearizing into propositions or passing to vector embeddings without normalization, embeddings treat `(1,240)` with positive cosine similarity to questions asking about *"positive capital additions"*, leading to wrong sign arithmetic in generation.

---

### Failure 3: In-Cell Footnote Citations Attached to Numbers

#### Real SEC 10-K Pattern:
```text
| Operating Margin (GAAP) | 18.4% (1) | 12.1% (2) |
```
Where Footnote (1) at the bottom of the page states:
*(1) Excludes $48.5 million of one-time litigation and photomask recalibration reserves.*

#### Why Existing Systems Crash:
- The string `18.4% (1)` breaks naive numerical parsers.
- The chunker slices the table without retrieving Footnote (1). The LLM reports `18.4%` as the definitive margin without knowing it includes non-recurring exclusions, resulting in an ungrounded audit error.

---

### Failure 4: Mid-Table Unit & Scale Transformations

#### Real SEC 10-K Pattern:
```text
| Consolidated Statements of Operations (in $ Millions, except per-share amounts) | 2026 |
| Net Revenue                                                                     | $412 |
| Operating Income                                                                | $48  |
| Common Shares Outstanding (in Thousands)                                        | 120,000 |
| Diluted Earnings Per Share (in Dollars)                                         | $0.31 |
| Effective Tax Rate (in Percent)                                                 | 18.5% |
```

#### Why Existing Systems Crash:
- Naive table chunkers extract the global banner (`in $ Millions`) and blindly prepend it to all rows.
- This creates erroneous propositions:
  - *Diluted EPS = $0.31 Million* (Overstated by $1,000,000\times$!)
  - *Effective Tax Rate = 18.5% Million* (Nonsensical).

---

### Failure 5: Ragged / Escaped Markdown Syntax

#### Real Pattern:
```text
| Segment | Adjusted Revenue (where |x| > 0) \| Notes | Q3 2026 |
```

#### Why Existing Systems Crash:
- Standard `row.split("|")` splits at `\|` and `|x|`, creating 6 tokens instead of 3, shifting all numbers by 2 columns to the right.
- `Q3 2026` becomes empty or receives the Notes column value.

