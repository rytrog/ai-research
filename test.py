import re

text = (
    "On March 14, 2026, Dr. Robert Vance met with Helios Semiconductor Corp. "
    "under Section 4.1 to inspect the Kronos-7 diode, i.e., Model K7-MED. "
    "The defect density was 0.42 defects/cm2, causing a $48.5 million penalty."
)

# 1. Naive Splitter (What most naive tutorials do)
naive_sents = re.split(r"[.?!]\s+", text)

# 2. Precision Boundary Engine
# When splitting on whitespace following a period, the characters immediately 
# before the whitespace include the period itself (e.g., 'Dr.', 'Corp.', 'i.e.')!
precision_pattern = re.compile(
    r"(?<!\bMr\.)(?<!\bMs\.)(?<!\bDr\.)(?<!\bJr\.)(?<!\bSr\.)"
    r"(?<!\bInc\.)(?<!\bLtd\.)(?<!\bCorp\.)(?<!\be\.g\.)(?<!\bi\.e\.)"
    r"(?<!\d\.)"  # Prevents splitting after decimals like 0.42 or $48.5
    r"(?<=[.!?])\s+"
    r"(?=[A-Z0-9\"'(\[])"
)
clean_sents = [s.strip() for s in precision_pattern.split(text) if s.strip()]

print("=" * 80)
print("--- 1. NAIVE SPLITTER (Broken Boundaries & Sliced Facts) ---")
print("=" * 80)
for i, s in enumerate(naive_sents, 1):
    print(f"[{i}] {s}")

print("\n" + "=" * 80)
print("--- 2. PRECISION BOUNDARY ENGINE (Clean, Intact Semantic Boundaries) ---")
print("=" * 80)
for i, s in enumerate(clean_sents, 1):
    print(f"[{i}] {s}")
print("=" * 80)
