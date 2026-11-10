import re

# Test the exact regex on the troublesome Chunk #10 sentence:
sentence_10 = "Consequently, the lower 1.80% royalty tier is locked in through December 31, 2026."
sentence_pronoun = "Consequently, it is locked in through December 31, 2026."

# Old pattern:
old_re = re.compile(
    r"^(?P<anaphor>"
    r"(?:It|They|He|She|Its|Their|यह|वे|इसने|उन्होंने|वह)\b"
    r"|(?:This|That|These|Those|Such|इस|उस|इन|उन)\s+(?P<dem_np>[a-zA-Z\u0900-\u097F\-]+(?:\s+[a-zA-Z\u0900-\u097F\-]+){0,2}?)(?=\s+(?:is|was|are|were|must|requires|mandates|has|had|can|will|should|may|shall|[a-z]+ed|[a-z]+es|[a-z]+s|को|में|ने|का|की|है|हैं)\b)"
    r"|The\s+(?P<def_np>[a-z][a-z\-]+(?:\s+[a-z][a-z\-]+){0,1}?)(?=\s+(?:is|was|are|were|must|requires|mandates|has|had|can|will|should|may|shall|[a-z]+ed|[a-z]+es|[a-z]+s)\b)"
    r"|(?P<adv_conj>Consequently|However|Therefore|Furthermore|Moreover|Accordingly|फलस्वरूप|हालांकि|इसलिए),\s+(?P<post_conj_subj>(?:it|they|he|she|this\s+[a-z\-]+|that\s+[a-z\-]+|the\s+[a-z0-9\.\-%\s]{2,35}?))(?=\s+(?:is|was|are|were|must|drops|dropped|applies|remains|requires|[a-z]+ed)\b)"
    r")",
    re.IGNORECASE,
)

# New precision pattern (strictly restricts post_conj_subj to genuine pronouns / demonstratives):
precision_re = re.compile(
    r"^(?P<anaphor>"
    r"(?:It|They|He|She|Its|Their|यह|वे|इसने|उन्होंने|वह)\b"
    r"|(?:This|That|These|Those|Such|इस|उस|इन|उन)\s+(?P<dem_np>[a-zA-Z\u0900-\u097F\-]+(?:\s+[a-zA-Z\u0900-\u097F\-]+){0,2}?)(?=\s+(?:is|was|are|were|must|requires|mandates|has|had|can|will|should|may|shall|[a-z]+ed|[a-z]+es|[a-z]+s|को|में|ने|का|की|है|हैं)\b)"
    r"|The\s+(?P<def_np>[a-z][a-z\-]+(?:\s+[a-z][a-z\-]+){0,1}?)(?=\s+(?:is|was|are|were|must|requires|mandates|has|had|can|will|should|may|shall|[a-z]+ed|[a-z]+es|[a-z]+s)\b)"
    r"|(?P<adv_conj>Consequently|However|Therefore|Furthermore|Moreover|Accordingly|फलस्वरूप|हालांकि|इसलिए),\s+(?P<post_conj_subj>(?:it|they|he|she|this\s+[a-z\-]+|that\s+[a-z\-]+))(?=\s+(?:is|was|are|were|must|drops|dropped|applies|remains|requires|[a-z]+ed)\b)"
    r")",
    re.IGNORECASE,
)

m_old = old_re.match(sentence_10)
m_new = precision_re.match(sentence_10)
m_pronoun = precision_re.match(sentence_pronoun)

print("Old Regex on 'Consequently, the lower 1.80% royalty tier...':")
print("   Matched:", m_old.group(0) if m_old else "None")

print("\nPrecision Regex on 'Consequently, the lower 1.80% royalty tier...':")
print("   Matched:", m_new.group(0) if m_new else "None (CLEAN - NOT AN ANAPHOR!)")

print("\nPrecision Regex on genuine pronoun 'Consequently, it is locked in...':")
print("   Matched:", m_pronoun.group(0) if m_pronoun else "None")
