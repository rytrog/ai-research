import re

PROTECTED_ABBREVIATIONS = [
    # Titles & Honorifics
    "mr", "mrs", "ms", "dr", "prof", "jr", "sr", "rev", "hon", "gov", "gen", "col", "capt", "sgt",
    # Corporate & Legal
    "inc", "ltd", "corp", "co", "llc", "llp", "gmbh", "pty", "pllc",
    # Scholarly & Latin
    "e.g", "i.e", "etc", "vs", "al", "ibid", "op", "cit", "ca", "cf",
    # Citations & Technical
    "sec", "art", "no", "vol", "fig", "eq", "ref", "dept", "div", "approx", "est", "avg", "min", "max",
    # Medical & Clinical
    "hba1c", "litt", "mg", "kg", "ml", "pt", "rx",
    # Academic Degrees
    "ph.d", "m.d", "b.a", "b.s", "m.a", "m.s", "ll.b", "ll.m",
]

def build_precision_sentence_splitter(custom_abbrs=None):
    abbr_list = list(PROTECTED_ABBREVIATIONS)
    if custom_abbrs:
        abbr_list.extend(custom_abbrs)
    
    # 1. Negative lookbehinds for protected abbreviations with trailing period
    lookbehinds = "".join(f"(?<!\\b{re.escape(abbr)}\\.)" for abbr in sorted(set(abbr_list)))
    
    # 2. Single letter initials (e.g. John F. Kennedy or A. Smith)
    initial_lookbehind = r"(?<!\b[A-Za-z]\.)"
    
    # 3. Numbered list item protection at start of lines: e.g. "1. " or "10. "
    # If a digit precedes a period at the start of a string or line, don't treat it as a previous sentence terminator!
    list_item_lookbehind = r"(?<!^\d\.)(?<!\n\d\.)(?<!^\d\d\.)(?<!\n\d\d\.)"
    
    # 4. Ellipsis protection (don't split inside '...')
    ellipsis_lookbehind = r"(?<!\.\.)"
    
    # 5. Sentence terminators: English (. ! ?), Hindi/Sanskrit (। ॥), Chinese/Japanese (。 ！？), Arabic (؟)
    terminators = r"(?<=[.!?।॥。！？\u061F])"
    
    # 6. Lookahead boundary: whitespace followed by uppercase, quotes, brackets, numbers, or non-Latin scripts
    boundary = r"\s+(?=[A-ZÀ-ÖØ-Þ0-9\"'(\[\u0900-\u097F\u4e00-\u9fff])"
    
    full_pattern = lookbehinds + initial_lookbehind + list_item_lookbehind + ellipsis_lookbehind + terminators + boundary
    return re.compile(full_pattern, flags=re.IGNORECASE)

splitter = build_precision_sentence_splitter()

test_text = (
    "On March 14, 2026, Dr. Robert Vance met with Helios Semiconductor Corp. "
    "under Sec. 4 to inspect the Kronos-7 diode, e.g., Model K7-MED. "
    "The defect density was 0.42 defects/cm2, causing a $48.5 million penalty! "
    "Prof. J. F. Smith from Dept. of Neuro-Optics reviewed Protocol NEURO-OPT-09. "
    "Next sentence starts here."
)

sents = [s.strip() for s in splitter.split(test_text) if s.strip()]
print(f"Total sentences found: {len(sents)}")
for i, s in enumerate(sents, 1):
    print(f"[{i}] {s}")
