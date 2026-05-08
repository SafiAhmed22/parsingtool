"""
Heading handling for the paraphrasing pipeline.

Rule (single threshold: 4 words on the heading line):

- **<= 4 words**: preserved exactly (__PRESERVE_HEADING__) — no rewrite.
- **> 4 words**: humanized via a dedicated GPT pass (__LONG_HEADING__), always
  kept on its own line(s), with clear blank separation before body text.

Markdown # words are counted without the hash run.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

HEADING_PRESERVE_MAX_WORDS = 4

# Markdown ATX headings:  # Title,  ## Title, etc.
_MD_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(\S.*)$")

# Multi-level numbered section:  2.1 Title,  3.2.1 Title,  2.1: Title
_MULTI_NUM_HEADING = re.compile(
    r"^\s*(\d+\.\d+(?:\.\d+)*)\s*[.:)\-–—]?\s*(\S.*)$"
)

# Single-level numbered section with MANDATORY separator: 1. Title, 2: Title, 3) Title
# First word of the title text must start with uppercase (to avoid matching body text).
_SINGLE_NUM_HEADING = re.compile(
    r"^\s*(\d{1,2})\s*[.:)]\s+([A-Z]\S*.*)$"
)

# Lone section index on its own line (PDF split):  2.1  or  3.2.1
_NUMBER_ONLY_LINE = re.compile(r"^\s*\d+\.\d+(?:\.\d+)*\s*$")

# Roman numeral section: IV. Methods
_ROMAN_HEADING = re.compile(
    r"^\s*([IVXLCDM]{1,8}|[ivxlcdm]{1,8})\.\s+(\S.*)$"
)

# Chapter / Appendix / Section labels
_LABELED_HEADING = re.compile(
    r"^\s*(Chapter|Appendix|Section|PART|Part)\s+.+$",
    re.IGNORECASE,
)


def heading_word_count(line: str) -> int:
    raw = line.rstrip("\r\n")
    m = _MD_HEADING.match(raw)
    if m:
        return len(m.group(2).strip().split())
    return len(raw.strip().split())


def is_heading_line(line: str) -> bool:
    raw = line.rstrip("\r\n")
    s = raw.strip()
    if not s:
        return False
    if _MD_HEADING.match(raw):
        return True
    if _MULTI_NUM_HEADING.match(raw):
        return True
    if _SINGLE_NUM_HEADING.match(raw):
        return True
    if _ROMAN_HEADING.match(raw):
        return True
    if _LABELED_HEADING.match(raw):
        return True
    return False


def _is_standalone_short_title_line(raw: str, allow: bool) -> bool:
    s = raw.strip()
    if not allow or not s:
        return False
    if s.endswith(".") or len(s) > 120:
        return False
    if s.startswith(("-", "*", "\u2022")) or re.match(r"^\d+\)", s):
        return False
    wc = heading_word_count(raw)
    if wc < 1 or wc > HEADING_PRESERVE_MAX_WORDS:
        return False
    words = s.split()

    def _title_like(w: str) -> bool:
        if w.isupper() and len(w) <= 5:
            return True
        if w[:1].isupper():
            return True
        if re.match(r"^\d", w):
            return True
        return w.lower() in {"and", "or", "of", "the", "a", "an", "to", "in", "on", "for"}

    return all(_title_like(w) for w in words)


def _is_standalone_long_title_line(raw: str, allow: bool) -> bool:
    s = raw.strip()
    if not allow or not s:
        return False
    if s.endswith(".") or len(s) > 180:
        return False
    wc = heading_word_count(raw)
    if wc <= HEADING_PRESERVE_MAX_WORDS or wc > 18:
        return False
    if s.startswith(("-", "*", "\u2022")) or re.match(r"^\d+\)", s):
        return False
    words = s.split()

    def _title_like(w: str) -> bool:
        if w.isupper() and len(w) <= 6:
            return True
        if w[:1].isupper():
            return True
        if re.match(r"^\d", w):
            return True
        return w.lower() in {"and", "or", "of", "the", "a", "an", "to", "in", "on", "for"}

    return all(_title_like(w) for w in words)


def line_should_preserve_heading(line: str, prev_blank: bool, first: bool) -> bool:
    raw = line.rstrip("\r\n")
    if not raw.strip():
        return False
    structural = is_heading_line(line)
    standalone = _is_standalone_short_title_line(raw, allow=(prev_blank or first))
    if not structural and not standalone:
        return False
    return heading_word_count(raw) <= HEADING_PRESERVE_MAX_WORDS


def line_is_long_heading(line: str, prev_blank: bool, first: bool) -> bool:
    raw = line.rstrip("\r\n")
    if not raw.strip():
        return False
    if is_heading_line(line) and heading_word_count(raw) > HEADING_PRESERVE_MAX_WORDS:
        return True
    if _is_standalone_long_title_line(raw, allow=(prev_blank or first)):
        return True
    return False


def heading_peel_role(line: str, idx: int, all_lines: List[str]) -> Optional[str]:
    raw = line.rstrip("\r\n")
    if not raw.strip():
        return None
    prev_blank = idx == 0 or not all_lines[idx - 1].strip()
    first = not any(all_lines[j].strip() for j in range(idx))
    if line_should_preserve_heading(line, prev_blank, first):
        return "preserve"
    if line_is_long_heading(line, prev_blank, first):
        return "long"
    return None


def _merge_split_section_numbers(text: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if _NUMBER_ONLY_LINE.match(cur) and cur.strip():
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                n2 = lines[j].strip()
                if n2 and len(n2) < 200 and not re.match(r"^[a-z]", n2):
                    out.append(f"{cur.strip()} {n2}")
                    i = j + 1
                    continue
        out.append(cur)
        i += 1
    return "\n".join(out)


def apply_heading_placeholders(text: str) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    if not text:
        return text, {}, {}

    merged = _merge_split_section_numbers(text)
    lines = merged.splitlines(keepends=True)
    preserve_map: Dict[str, str] = {}
    long_map: Dict[str, str] = {}
    out: List[str] = []
    prev_blank = True
    seen_nonempty = False

    for line in lines:
        is_blank = not line.strip()
        first = not seen_nonempty and not is_blank
        raw = line.rstrip("\r\n")

        if line_should_preserve_heading(line, prev_blank, first):
            ph = f"__PRESERVE_HEADING_{len(preserve_map)}__"
            preserve_map[ph] = raw
            out.append(ph + "\n")
        elif line_is_long_heading(line, prev_blank, first):
            ph = f"__LONG_HEADING_{len(long_map)}__"
            long_map[ph] = raw
            out.append(ph + "\n")
        else:
            out.append(line)

        if not is_blank:
            seen_nonempty = True
        prev_blank = is_blank

    return "".join(out), preserve_map, long_map


def restore_heading_placeholders(text: str, mapping: Dict[str, str]) -> str:
    restored = text
    for ph, original in mapping.items():
        restored = restored.replace(ph, original)
    return restored
