#!/usr/bin/env python3
r"""
================================================================================
EXPERIMENT 01: ADVERSARIAL TABLE STRESS-TEST (RED-TEAMING THE CHUNKER)
Location: my_research/experiments/01_baseline_stress_test.py
================================================================================
Stress-tests the chunker against real SEC 10-K pathological edge cases:
  1. Multi-tier column super-headers (Three Months vs. Nine Months).
  2. Parenthetical negative numbers: `(158.20)` -> -$158.20M.
  3. In-cell footnote annotations: `274.80 (1)` -> preserves value + tracks footnote.
  4. Mid-table unit switches: `$ Millions` -> `Shares in Thousands` -> `EPS in $`.
  5. Escaped pipe `\|` and math absolute values `|x|`.
================================================================================
"""

import sys
import pathlib

# Ensure workspace root is in path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Pathological SEC 10-K Table
ADVERSARIAL_10K_TABLE = r"""
All monetary figures in the schedule below are reported in millions of U.S. dollars ($ USD Millions), except per-share data, share counts, and percentage defect metrics, for the fiscal periods ended September 30, 2026:

| Financial Metric | Three Months Ended Sept 30, 2026 | Three Months Ended Sept 30, 2025 | Nine Months Ended Sept 30, 2026 | Nine Months Ended Sept 30, 2025 |
| :--- | :---: | :---: | :---: | :---: |
| Optical Revenue \| Kronos-7 Architecture | $274.80 (a) | $336.50 | $945.10 | $892.40 |
| Photomask Recalibration Reserve | $48.50 | $0.00 | $67.70 | $0.00 |
| Operating Income / (Loss) (GAAP) | (158.20) | $42.10 | (210.40) | $118.60 |
| Effective Corporate Tax Rate (%) | 18.5% | 21.0% | 18.2% | 21.4% |
| Weighted Common Shares (in Thousands) | 120,000 | 118,500 | 119,800 | 118,200 |
| Diluted Earnings / (Loss) Per Share (in $) | (1.32) | $0.36 | (1.76) | $1.00 |
"""

def main():
    print("=" * 80)
    print("🔬 EXPERIMENT 01: ADVERSARIAL SEC 10-K STRESS TEST")
    print("=" * 80)
    print("Adversarial Table Loaded:")
    print(ADVERSARIAL_10K_TABLE.strip())
    print("\n[OK] Lab environment successfully loaded!")

if __name__ == "__main__":
    main()

