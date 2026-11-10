# 🔬 D-COMP RESEARCH LAB: ADVERSARIAL TABULAR & MULTI-HOP RAG

> **Guiding Principle:** *"We do not blindly trust theoretical claims or toy benchmarks. Every mechanism must be stress-tested against worst-case, adversarial enterprise documents until it cannot break."*

---

## 🎯 The Research Mission
- **Target Problem:** Eliminating the 80%+ failure ceiling on **Structured Numerical & Tabular Data** in enterprise documents (SEC 10-K/10-Q filings, financial schedules, clinical protocols).
- **Core Hypothesis:** SOTA systems fail either because they slice tables blindly (losing 2D coordinates, accounting flow, and units) or because they rely on prohibitively slow LLM extraction (e.g., EnSI-RAG taking 468s per query). A **deterministic, compiler-guided dual-view architecture** can eliminate coordinate loss in $<15\text{ ms}$ with zero source text mutation.
- **Benchmark Ceiling to Break:** FinanceBench (Patronus AI), TAT-QA, and complex SEC 10-K multi-hop queries.

---

## 📁 Research Laboratory Structure

```
my_research/
├── README.md               # Research manifesto and architectural standards
├── RESEARCH_LOG.md         # Daily hypothesis, experimental logs, and ablation notes
├── src/                    # Hardened, modular engine implementation
│   ├── parser/             # Deterministic AST, table geometry, and boundary parsers
│   ├── chunker/            # Knapsack token packers & dual-view compilers
│   ├── indexing/           # Dense vectors + O(1) symbolic handle indexes
│   └── retrieval/          # Dual-axis retrieval and deterministic auto-merging
├── data/                   # Real-world & adversarial datasets
│   ├── sec_filings/        # Raw 10-K filings (Apple, Microsoft, Tesla, etc.)
│   └── adversarial_cases/  # Edge cases designed to break naive RAG
├── experiments/            # Isolated ablation scripts and benchmark runs
├── eval/                   # Automated evaluation harness (Recall@K, EM, F1, Latency)
└── analysis/               # Deep-dive error audits, failure catalogs, and profiling
```

---

## 🛡️ The 7 Worst-Case Stress Tests We Must Pass

We will not claim a solution works until it survives these 7 edge cases without human intervention:

1. **Multi-Level / Hierarchical Headers:** (e.g., Year super-headers over quarterly sub-headers).
2. **Parenthetical Negative Accounting:** `(48.50)` correctly interpreted as `-$48.50`, not positive `$48.50`.
3. **In-Cell Footnotes:** `$412.40 (1)` parsed cleanly without breaking numerical alignment or regexes.
4. **Mid-Table Unit Shifts:** Rows 1–10 in `$ Millions`, Row 11 in `Shares in Thousands`, Row 12 in `%`.
5. **Irregular / Ragged Markdown Pipes:** Escaped pipes `\|`, absolute values `|x|`, and uneven cell counts.
6. **Contiguous Accounting Flow:** Ensuring calculations like $\text{Gross Profit} - \text{OpEx} = \text{EBIT}$ are never severed across arbitrary boundaries.
7. **Strict Context Budget Guarantee:** No chunk ever overflows the transformer limit under native subword BPE tokenization.

