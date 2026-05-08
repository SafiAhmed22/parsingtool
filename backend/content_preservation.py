"""
Extract and restore citations, defined acronyms, and post-process output artifacts.
Addresses client feedback on citation integrity, garbled acronyms, and formatting noise.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Phrases that must not be paraphrased into wrong frameworks or garbled (case-sensitive variants).
DEFAULT_ACADEMIC_SAFELIST: List[str] = [
    "Porter's Five Forces",
    "Porter’s Five Forces",
    "Five Forces",
    "Porter Five Forces",
    "SWOT",
    "SWOT analysis",
    "PESTLE",
    "PESTEL",
    "Total Addressable Market",
    "TAM",
    "Serviceable Addressable Market",
    "SAM",
    "Serviceable Obtainable Market",
    "SOM",
    "PwC",
    "PricewaterhouseCoopers",
    "Business Model Canvas",
    "Osterwalder",
    "Pigneur",
    "Big Data",
    "Machine Learning",
    "machine learning",
    "Artificial Intelligence",
    "artificial intelligence",
    "activism",
    "craftivism",
]

_YEAR = re.compile(r"\b(19|20)\d{2}\b")

# Author–year narrative citation patterns.
# Supports 1, 2, or 3+ authors with mixed comma/and/&.
# Examples captured:
#   Smith (2020)
#   Smith and Jones (2020)
#   Smith & Jones (2020)
#   Smith, Jones and Brown (2020)
#   Serrano-Cinca, Fuertes-Callen and Cuellar-Fernandez (2021)
#   Bukar, Usman and Ngubdo (2025)
_NAME = r"[A-Z][a-zA-Z'\u2019\-]*"
_RE_AUTH_PAREN_YEAR = re.compile(
    rf"\b{_NAME}"
    rf"(?:,\s*{_NAME})*"
    rf"(?:\s*(?:&|and)\s*{_NAME})?"
    rf"\s*\(\s*(?:19|20)\d{{2}}[a-z]?\s*\)"
)

# Multi-word title before acronym: "Total Addressable Market (TAM)"
_RE_DEFINED_ACRONYM = re.compile(
    r"\b((?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){1,14})\s+\(([A-Z]{2,10})\)(?=[\s.,;:!?)\]]|$)"
)


def _looks_like_citation_segment(paren_content: str) -> bool:
    inner = paren_content[1:-1]
    if len(inner) > 320:
        return False
    if not _YEAR.search(inner):
        return False
    letters = re.sub(r"[^A-Za-z]", "", inner)
    return len(letters) >= 3


def _balanced_paren_spans(text: str) -> List[Tuple[int, int, str]]:
    spans: List[Tuple[int, int, str]] = []
    n = len(text)
    i = 0
    while i < n:
        if text[i] != "(":
            i += 1
            continue
        depth = 0
        j = i
        while j < n:
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    seg = text[i : j + 1]
                    if _looks_like_citation_segment(seg):
                        spans.append((i, j + 1, seg))
                    i = j + 1
                    break
            j += 1
        else:
            i += 1
    return spans


def _merge_non_overlapping(
    spans: List[Tuple[int, int, str]]
) -> List[Tuple[int, int, str]]:
    if not spans:
        return []
    spans = sorted(spans, key=lambda x: x[0])
    out: List[Tuple[int, int, str]] = []
    cur_s, cur_e, cur_t = spans[0]
    for s, e, t in spans[1:]:
        if s < cur_e:
            if e - s > cur_e - cur_s:
                cur_s, cur_e, cur_t = s, e, t
        else:
            out.append((cur_s, cur_e, cur_t))
            cur_s, cur_e, cur_t = s, e, t
    out.append((cur_s, cur_e, cur_t))
    return out


def _subtract_spans(
    base: List[Tuple[int, int, str]], mask: List[Tuple[int, int]]
) -> List[Tuple[int, int, str]]:
    if not mask:
        return base
    mask = sorted(mask)
    res: List[Tuple[int, int, str]] = []
    for s, e, t in base:
        ok = True
        for ms, me in mask:
            if not (e <= ms or s >= me):
                ok = False
                break
        if ok:
            res.append((s, e, t))
    return res


def apply_citation_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """Replace parenthetical citations and Author (Year) patterns with placeholders."""
    if not text:
        return text, {}

    spans = _merge_non_overlapping(_balanced_paren_spans(text))
    auth_spans: List[Tuple[int, int, str]] = []
    for m in _RE_AUTH_PAREN_YEAR.finditer(text):
        auth_spans.append((m.start(), m.end(), m.group(0)))
    auth_spans = _merge_non_overlapping(auth_spans)
    cite_mask = [(a, b) for a, b, _ in spans]
    auth_spans = _subtract_spans(auth_spans, cite_mask)

    all_spans = _merge_non_overlapping(spans + auth_spans)
    all_spans.sort(key=lambda x: x[0])

    mapping: Dict[str, str] = {}
    parts: List[str] = []
    last = 0
    for idx, (st, en, substr) in enumerate(all_spans):
        ph = f"__PRESERVE_CITE_{idx}__"
        mapping[ph] = substr
        parts.append(text[last:st])
        parts.append(ph)
        last = en
    parts.append(text[last:])
    return "".join(parts), mapping


def restore_citation_placeholders(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for ph, orig in mapping.items():
        out = out.replace(ph, orig)
    out = _fix_citation_spacing(out)
    return out


def _fix_citation_spacing(text: str) -> str:
    """Ensure correct spacing & punctuation around restored citations.

    Fixes (client feedback PDF examples):
      - ``(Burns 1978)The``         → ``(Burns 1978) The``
      - ``word(Burns 1978)``        → ``word (Burns 1978)``
      - ``and.(Author, 2025)``      → ``and (Author, 2025)``      (orphan period)
      - ``thought.(Author, 2021)``  → ``thought (Author, 2021)``  (when paren ends mid-clause)
      - ``,( Author, 2020)``        → ``, (Author, 2020)``
      - duplicate spaces / spaces before commas/periods
    """
    if not text:
        return text

    # Strip stray period or comma immediately before opening paren that follows
    # a connecting word (and/but/or/so/yet/nor/while/whereas/although/because/where/when).
    text = re.sub(
        r"\b(and|but|or|so|yet|nor|while|whereas|although|because|where|when)\s*[.,;:]\s*\(",
        r"\1 (",
        text,
        flags=re.IGNORECASE,
    )

    # Normalise space between opening paren and content
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)

    # Ensure space before opening paren when preceded by a letter or digit
    text = re.sub(r"([A-Za-z0-9])\(", r"\1 (", text)

    # Ensure space after closing paren when followed by a letter
    text = re.sub(r"\)([A-Za-z])", r") \1", text)

    # Collapse double spaces, fix `space + punctuation`
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([.,;:!?])", r"\1", text)

    return text


def apply_acronym_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """Freeze 'Defined Term (ABC)' so models do not garble acronyms or expansions."""
    if not text:
        return text, {}

    matches: List[Tuple[int, int, str]] = []
    for m in _RE_DEFINED_ACRONYM.finditer(text):
        full = m.group(0)
        if len(full) > 120:
            continue
        matches.append((m.start(), m.end(), full))

    matches = _merge_non_overlapping(matches)
    matches.sort(key=lambda x: x[0])

    mapping: Dict[str, str] = {}
    parts: List[str] = []
    last = 0
    for idx, (st, en, substr) in enumerate(matches):
        ph = f"__PRESERVE_ACRONYM_{idx}__"
        mapping[ph] = substr
        parts.append(text[last:st])
        parts.append(ph)
        last = en
    parts.append(text[last:])
    return "".join(parts), mapping


def restore_acronym_placeholders(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for ph, orig in mapping.items():
        out = out.replace(ph, orig)
    out = _fix_citation_spacing(out)
    return out


def dedupe_adjacent_years(text: str) -> str:
    """Fix duplicated years e.g. (Name 2010, 2010)."""
    return re.sub(r"(\b(?:19|20)\d{2}\b)\s*,\s*\1\b", r"\1", text)


def sanitize_artifacts(text: str) -> str:
    """Remove long decorative dash/underscore runs and tidy spacing."""
    if not text:
        return text
    text = re.sub(r"(?:[\-\u2010-\u2015_=]){8,}", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def source_uses_markdown_headings(text: str) -> bool:
    """True if the user document already uses ATX # headings (do not strip later)."""
    return bool(re.search(r"(?m)^\s{0,3}#{1,6}\s+\S", text))


def strip_spurious_markdown(text: str, source_had_markdown: bool) -> str:
    """
    If the source had no markdown headings, remove accidental # / ** from model output
    (Analysis_Feedback: visible markdown traces).
    """
    if not text or source_had_markdown:
        return text
    out_lines: List[str] = []
    for ln in text.splitlines():
        s = re.sub(r"^\s{0,3}#{1,6}\s+", "", ln)
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s)
        out_lines.append(s)
    return "\n".join(out_lines)


def collapse_stutter_repetition(text: str) -> str:
    """Reduce patterns like 'X and X and X' (client feedback on repetition)."""
    if not text:
        return text
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        cur = re.sub(
            r"\b(\w+)\b(?:\s+and\s+\b\1\b)+",
            r"\1",
            cur,
            flags=re.IGNORECASE,
        )
    return cur


# Patterns the rewriter is known to inflate (PDF feedback).
_REDUNDANCY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # "within the context of this context" → "within this context"
    (re.compile(r"\bwithin\s+the\s+context\s+of\s+this\s+context\b", re.IGNORECASE),
     "within this context"),
    # "in the context of this context" → "in this context"
    (re.compile(r"\bin\s+the\s+context\s+of\s+this\s+context\b", re.IGNORECASE),
     "in this context"),
    # generic "X of this X" duplicate noun (e.g., "process of this process")
    (re.compile(r"\b(\w+)\s+of\s+this\s+\1\b", re.IGNORECASE), r"this \1"),
    # "more X-er" awkward chains
    (re.compile(r"\bmore\s+(\w+er)\b", re.IGNORECASE), r"\1"),
    # Repeated adjacent identical word ("very very", "the the")
    (re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE), r"\1"),
    # Trailing/leading apostrophe garbage like "skills.'" at end of sentence
    (re.compile(r"([A-Za-z])\s*\.[\u2018\u2019']"), r"\1."),
    # "and , " → ", and"
    (re.compile(r"\band\s*,\s*"), ", and "),
    # double "in addition," start
    (re.compile(r"\b(in addition|moreover|furthermore)[,]?\s+\1\b", re.IGNORECASE), r"\1"),
]


def collapse_redundant_phrases(text: str) -> str:
    """Remove redundant academic-rewriter artefacts flagged by the QA team."""
    if not text:
        return text
    out = text
    for pat, repl in _REDUNDANCY_PATTERNS:
        prev = None
        while prev != out:
            prev = out
            out = pat.sub(repl, out)
    return out


# Tokens the local T5 humanizer is known to leak ("paraphraser:", odd
# fragments). The PDF also showed split words like "Globalisa on" — those come
# from the humanizer breaking placeholder underscores. We can't recover the
# exact word post-hoc, but we can at least normalise spacing.
def normalise_whitespace(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_paraphraser_tag(text: str) -> str:
    """Remove leaked 'paraphraser' tags the humanizer model sometimes echoes into output."""
    if not text:
        return text
    text = re.sub(r":?\s*[Pp]araphraser\s*[:.]?\s*", " ", text)
    text = re.sub(r"  +", " ", text)
    text = re.sub(r" +([.,;:!?])", r"\1", text)
    return text


def build_safelist_terms(extra: Optional[List[str]] = None) -> List[str]:
    out: List[str] = []
    for t in DEFAULT_ACADEMIC_SAFELIST + (extra or []):
        if t and t not in out:
            out.append(t)
    return out
