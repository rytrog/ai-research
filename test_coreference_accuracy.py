import re
from typing import List, Optional, Set, Tuple

# Test entities
ENT_HUMAN_SINGULAR = "HUMAN_SINGULAR"
ENT_ORG_LEGAL = "ORG_LEGAL"
ENT_PLURAL_GROUP = "PLURAL_GROUP"
ENT_CONCEPT_NOMINAL = "CONCEPT_NOMINAL"
ENT_PROPER_PERSON_OR_ORG = "PROPER_PERSON_OR_ORG"  # Solves the John Smith bug!

HUMAN_TITLES = {
    "dr", "dr.", "mr", "mr.", "ms", "ms.", "mrs", "mrs.", "prof", "prof.",
    "professor", "ceo", "cfo", "cto", "president", "director", "chairman",
    "judge", "justice", "senator", "surgeon", "physician", "investigator",
}

ORG_SUFFIXES = {
    "corp", "corp.", "corporation", "inc", "inc.", "incorporated",
    "ltd", "ltd.", "limited", "llc", "l.l.c.", "plc", "lp", "llp",
    "gmbh", "ag", "sa", "nv", "bv", "holdings", "partners", "group",
    "bank", "trust", "fund", "capital", "ventures", "securities",
    "hospital", "university", "institute", "college", "clinic", "school",
    "foundation", "association", "committee", "commission", "council",
    "board", "agency", "authority", "ministry", "department", "court",
    "technologies", "semiconductor", "photonics", "pharmaceuticals",
    "therapeutics", "biosciences", "systems", "solutions", "laboratories", "labs",
}

def classify_entity_type(span: str) -> str:
    tokens = [t.strip(".,;:()") for t in span.split() if t.strip(".,;:()")]
    if not tokens:
        return ENT_CONCEPT_NOMINAL
    low_tokens = [t.lower() for t in tokens]

    # Explicit human title
    if low_tokens[0] in HUMAN_TITLES:
        return ENT_HUMAN_SINGULAR

    # Explicit organization suffix
    if any(w in ORG_SUFFIXES for w in low_tokens):
        return ENT_ORG_LEGAL

    # Plural group
    if low_tokens[-1] in {"partners", "holdings", "associates", "auditors", "patients", "surgeons"}:
        return ENT_PLURAL_GROUP

    # Title-cased proper phrase without org suffix (e.g., "John Smith", "Robert Vance", "Sarah Lin", "Helios")
    if all(t[0].isupper() for t in tokens if t.lower() not in {"of", "for", "and", "&", "de", "van", "von"}):
        # If it's a 2 or 3 word capitalized phrase without corporate suffix, it is a high-probability Person or Named Entity!
        if len(tokens) in (2, 3):
            return ENT_PROPER_PERSON_OR_ORG
        return ENT_ORG_LEGAL

    return ENT_CONCEPT_NOMINAL

# Test classification on key entities:
test_names = [
    "John Smith",
    "Dr. Robert Vance",
    "Sarah Lin",
    "Helios Semiconductor Corp.",
    "Aether Photonics Ltd.",
    "Meridian Vault IP Holdings LLC",
    "Audit Committee",
    "the lower 1.80% royalty tier",
    "Kronos-7"
]

print("=" * 70)
print("ENTITY CLASSIFICATION AUDIT:")
print("=" * 70)
for name in test_names:
    etype = classify_entity_type(name)
    print(f"'{name}' -> {etype}")

# Compatibility check for pronoun 'He' / 'She' vs 'It' / 'They':
print("\n" + "=" * 70)
print("PRONOUN COMPATIBILITY AUDIT:")
print("=" * 70)
for name in ["John Smith", "Dr. Robert Vance", "Helios Semiconductor Corp."]:
    etype = classify_entity_type(name)
    compatible_with_he = etype in (ENT_HUMAN_SINGULAR, ENT_PROPER_PERSON_OR_ORG)
    compatible_with_it = etype in (ENT_ORG_LEGAL, ENT_PROPER_PERSON_OR_ORG, ENT_CONCEPT_NOMINAL)
    print(f"'{name}' ({etype}):")
    print(f"   Can resolve 'He/She'? -> {compatible_with_he}")
    print(f"   Can resolve 'It'?     -> {compatible_with_it}")
