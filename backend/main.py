import os
import re
import getpass
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from chunkingengine import Chunk, chunk_text, get_text_from_user
from content_preservation import (
    apply_acronym_placeholders,
    apply_citation_placeholders,
    build_safelist_terms,
    collapse_redundant_phrases,
    collapse_stutter_repetition,
    dedupe_adjacent_years,
    normalise_whitespace,
    restore_acronym_placeholders,
    restore_citation_placeholders,
    sanitize_artifacts,
    source_uses_markdown_headings,
    strip_paraphraser_tag,
    strip_spurious_markdown,
)
from heading_preservation import (
    apply_heading_placeholders,
    heading_peel_role,
    heading_word_count,
    restore_heading_placeholders,
)
from pipeline import HumanizationPipeline

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _name in ("env", ".env"):
    _p = os.path.join(_BASE_DIR, _name)
    if os.path.isfile(_p):
        load_dotenv(_p)
load_dotenv()


TERM_TAG_PATTERN = re.compile(r"<term>(.*?)</term>", re.IGNORECASE | re.DOTALL)
_FROZEN_HEADING_LINE = re.compile(r"^\s*__PRESERVE_HEADING_(\d+)__\s*$")
_LONG_HEADING_LINE = re.compile(r"^\s*__LONG_HEADING_(\d+)__\s*$")
_INLINE_PLACEHOLDER = re.compile(
    r"__(?:PROTECTED_TERM|PRESERVE_CITE|PRESERVE_ACRONYM|LONG_HEADING)_\d+__"
)
_INLINE_SPLIT = re.compile(
    r"(__(?:PROTECTED_TERM|PRESERVE_CITE|PRESERVE_ACRONYM|LONG_HEADING)_\d+__)"
)


def _strength_instruction(level: str) -> str:
    """Map slider strength to a rewriting style description."""
    if level == "easy":
        return (
            "Rewriting strength: LOW. Use light paraphrasing — change wording sentence "
            "by sentence but keep the same sentence count, the same paragraph order, "
            "and most original phrasing intact. Do NOT compress paragraphs into "
            "long run-on sentences. Do NOT delete content."
        )
    if level == "hard":
        return (
            "Rewriting strength: HIGH. Restructure each sentence with new word order "
            "and clause arrangement, but keep the SAME meaning, the SAME facts, and the "
            "SAME number of sentences per paragraph. Do NOT introduce new claims, new "
            "examples, new frameworks, or any term that is not already in the source."
        )
    return (
        "Rewriting strength: MEDIUM. Rewrite each sentence in your own words with new "
        "syntax, but keep the same meaning, the same number of sentences per paragraph, "
        "and the same factual content. No new claims, examples, frameworks, or terms."
    )


def _rewrite_system_instructions(tone: str, level: str = "medium") -> str:
    return (
        "You are an academic copy-editor who paraphrases scholarly text. Output only the "
        "paraphrased text — no preamble, no explanation, no markdown.\n"
        + tone_instruction(tone) + "\n"
        + _strength_instruction(level) + "\n"
        "STRICT RULES (must obey all):\n"
        "1. MEANING PRESERVATION — keep every claim, fact, definition, number, name, "
        "year and quotation accurate. Never invent terms, frameworks, or examples.\n"
        "2. NO FABRICATION — do not introduce phrases not implied by the source "
        "(forbidden examples seen in QA: 'rare and omniscient skill', 'Green Energy "
        "Management system', 'within the context of this context'). If unsure, keep "
        "the source wording.\n"
        "3. SENTENCE PARITY — each paragraph must have approximately the same number "
        "of sentences as the source paragraph. Do not merge sentences into run-ons. "
        "Do not split a single sentence into many fragments.\n"
        "4. PARAGRAPH STRUCTURE — keep the input paragraph breaks (blank lines).\n"
        "5. LENGTH — keep the rewrite within roughly 90–110% of the source word count "
        "for each paragraph.\n"
        "6. CITATION ANCHORING — every in-text citation placeholder "
        "__PRESERVE_CITE_<digits>__ MUST appear EXACTLY ONCE in the output, in "
        "the SAME relative order as the source, and MUST remain in the SAME "
        "sentence as the claim it supports. Do not move a citation to a "
        "different sentence, do not split a citation across sentences, do not "
        "merge two citations, and do not duplicate one. Keep punctuation around "
        "citations clean: a citation at the end of a sentence is followed by a "
        "period (or comma) AFTER the closing parenthesis, never before. Never "
        "write patterns like 'and.(', 'thought.(', 'word.(', or '.(' before a "
        "citation.\n"
        "7. PROTECTED TERMS — every __PROTECTED_TERM_<digits>__, __PRESERVE_CITE_<digits>__, "
        "__PRESERVE_ACRONYM_<digits>__, __PRESERVE_HEADING_<digits>__ and "
        "__LONG_HEADING_<digits>__ token MUST be reproduced character-for-character "
        "with a SPACE on both sides (do not glue them to adjacent words, do not insert "
        "punctuation inside them, do not split them).\n"
        "8. NAMED ENTITIES — preserve all proper nouns, organisation names, brand "
        "names, model names, and established framework names exactly (e.g., never "
        "rename 'Porter's Five Forces' to 'Six Forces' or any variant; keep TAM, "
        "SAM, SOM, PwC, SWOT, PESTEL, Business Model Canvas as written).\n"
        "9. NO REDUNDANCY — do not write tautologies such as 'within the context of "
        "this context', 'process of this process', or repeat the same word "
        "back-to-back.\n"
        "10. NO MARKDOWN — no #, **, *, bullets, or decorative dashes unless the "
        "input already uses them.\n"
        "11. NO YEAR DUPLICATION — never write a year twice in the same citation "
        "(forbidden: '2010, 2010').\n"
    )


def _rewrite_system_instructions_legacy(tone: str) -> str:
    """Kept for callers that don't pass a strength level."""
    return _rewrite_system_instructions(tone, "medium")


def select_tone() -> str:
    print("")
    print("Step 1: Select tone:")
    print("  1. phd_academic      - PhD dissertation level")
    print("  2. standard_academic - Graduate / undergraduate level")
    print("  3. esl_simple        - Simple, accessible academic English")
    tone_map = {"1": "phd_academic", "2": "standard_academic", "3": "esl_simple"}
    while True:
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice in tone_map:
            return tone_map[choice]
        print("Invalid. Please enter 1, 2, or 3.")


def select_humanization_level() -> str:
    print("")
    print("Step 2: Humanization level:")
    print("  1. easy")
    print("  2. medium")
    print("  3. hard")
    level_map = {"1": "easy", "2": "medium", "3": "hard"}
    while True:
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice in level_map:
            return level_map[choice]
        print("Invalid. Please enter 1, 2, or 3.")


def tone_instruction(tone: str) -> str:
    if tone == "phd_academic":
        return "Use an advanced PhD-level academic tone."
    if tone == "esl_simple":
        return "Use clear and simple academic English suitable for ESL readers."
    return "Use a standard academic tone suitable for graduate/undergraduate writing."


def humanization_temperature(level: str) -> float:
    """Temperature now varies with strength, but stays low to avoid fabrication.

    Client feedback: the 'hard' (high) mode introduced fabricated terms.
    Keeping temperature low + stricter prompt fixes that.
    """
    if level == "easy":
        return 0.45
    if level == "hard":
        return 0.55
    return 0.5


def parse_xml_protected_terms(text: str) -> Tuple[str, List[str]]:
    terms: List[str] = []

    def _collect(match: re.Match) -> str:
        term_text = match.group(1).strip()
        if term_text:
            terms.append(term_text)
            return term_text
        return ""

    cleaned_text = TERM_TAG_PATTERN.sub(_collect, text)
    return cleaned_text, terms


def collect_manual_protected_terms() -> List[str]:
    print("")
    print("Step 3: Optional extra protected terms (comma-separated), or press Enter to skip:")
    raw_terms = input().strip()
    if not raw_terms:
        return []
    return [t.strip() for t in raw_terms.split(",") if t.strip()]


def build_protected_map(terms: List[str]) -> Dict[str, str]:
    unique_terms: List[str] = []
    for t in terms:
        if t and t not in unique_terms:
            unique_terms.append(t)
    return {f"__PROTECTED_TERM_{idx}__": term for idx, term in enumerate(unique_terms)}


def apply_protection(text: str, protected_map: Dict[str, str]) -> str:
    """
    Wrap protected terms with the placeholder, ensuring whitespace on both
    sides so downstream models cannot glue the placeholder to a neighbouring
    word (which produced "Globalisa onA world" in client feedback).
    """
    protected_text = text
    # Sort by length descending to protect longer overlapping terms first.
    sorted_items = sorted(protected_map.items(), key=lambda kv: len(kv[1]), reverse=True)
    for placeholder, term in sorted_items:
        if not term:
            continue
        # Pad with spaces only if neighbour is alphanumeric — preserves
        # punctuation immediately after the term (e.g., "TAM,").
        padded = " " + placeholder + " "
        protected_text = protected_text.replace(term, padded)
    # Collapse the doubled whitespace introduced by the padding.
    protected_text = re.sub(r"[ \t]{2,}", " ", protected_text)
    protected_text = re.sub(r" ([.,;:!?])", r"\1", protected_text)
    return protected_text


# Patterns that match a placeholder even after the local humanizer has
# inserted spaces inside the underscores.  Example failures from PDF feedback:
#   "Globalisa on" / "Globalisa onA" → __PROTECTED_TERM_<n>__
#   "_ _ PROTECTED _ TERM _ 0 _ _"  → __PROTECTED_TERM_0__
_PROTECTED_TERM_BROKEN = re.compile(
    r"_\s*_\s*PROTECTED\s*_\s*TERM\s*_\s*(\d+)\s*_\s*_",
    re.IGNORECASE,
)
_PRESERVE_CITE_BROKEN = re.compile(
    r"_\s*_\s*PRESERVE\s*_\s*CITE\s*_\s*(\d+)\s*_\s*_",
    re.IGNORECASE,
)
_PRESERVE_ACRONYM_BROKEN = re.compile(
    r"_\s*_\s*PRESERVE\s*_\s*ACRONYM\s*_\s*(\d+)\s*_\s*_",
    re.IGNORECASE,
)
_LONG_HEADING_BROKEN = re.compile(
    r"_\s*_\s*LONG\s*_\s*HEADING\s*_\s*(\d+)\s*_\s*_",
    re.IGNORECASE,
)
_PRESERVE_HEADING_BROKEN = re.compile(
    r"_\s*_\s*PRESERVE\s*_\s*HEADING\s*_\s*(\d+)\s*_\s*_",
    re.IGNORECASE,
)


def repair_broken_placeholders(text: str) -> str:
    """Restore placeholders the humanizer mangled by inserting spaces inside underscores."""
    if not text:
        return text
    text = _PROTECTED_TERM_BROKEN.sub(lambda m: f"__PROTECTED_TERM_{m.group(1)}__", text)
    text = _PRESERVE_CITE_BROKEN.sub(lambda m: f"__PRESERVE_CITE_{m.group(1)}__", text)
    text = _PRESERVE_ACRONYM_BROKEN.sub(lambda m: f"__PRESERVE_ACRONYM_{m.group(1)}__", text)
    text = _LONG_HEADING_BROKEN.sub(lambda m: f"__LONG_HEADING_{m.group(1)}__", text)
    text = _PRESERVE_HEADING_BROKEN.sub(lambda m: f"__PRESERVE_HEADING_{m.group(1)}__", text)
    return text


def restore_protection(text: str, protected_map: Dict[str, str]) -> str:
    restored_text = repair_broken_placeholders(text)
    for placeholder, term in protected_map.items():
        restored_text = restored_text.replace(placeholder, term)
    # Re-introduce a space when a letter is glued to a paren after restoration.
    restored_text = re.sub(r"\)([A-Za-z])", r") \1", restored_text)
    restored_text = re.sub(r"([A-Za-z])\(", r"\1 (", restored_text)
    # Tidy the padding we added in apply_protection.
    restored_text = re.sub(r"[ \t]{2,}", " ", restored_text)
    restored_text = re.sub(r" ([.,;:!?])", r"\1", restored_text)
    return restored_text


def rewrite_long_heading(
    pipeline: HumanizationPipeline,
    heading_line: str,
    tone: str,
) -> str:
    """Rewrite a multi-word structural heading in one line; keeps numbering when present."""
    original = heading_line.strip()
    if not original:
        return original
    try:
        response = pipeline.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You rewrite ONE document section heading so it sounds natural and human-written "
                        "(clear, fluent, professional). Output exactly ONE line — no second line, no quotes. "
                        "Keep section numbering or prefixes exactly as in the input (e.g. 2.1, 2.1:, ##, IV.). "
                        "Do not change factual meaning; you may tighten wording for readability. "
                        "Do not merge with body text; this line must stand alone as a title. "
                        "No markdown added unless the input already uses it. "
                        "No trailing period unless the original had one. "
                        "Never return an empty response. "
                        + tone_instruction(tone)
                    ),
                },
                {"role": "user", "content": "Heading line:\n" + original},
            ],
            temperature=0.45,
        )
        out = (response.choices[0].message.content or "").strip()
        one = out.split("\n")[0].strip() if out else original
        return one if one else original
    except Exception:
        return original


# Analysis_Feedback: T5 grammar_fix often introduced doubled letters / typos — disabled for body text.
USE_LOCAL_GRAMMAR_FIX = False

# Client feedback Apr 2026: the local T5 humanizer (NoaiGPT/777) is the source
# of most fabricated terms ("rare and omniscient skill", "Green Energy
# Management system") AND mangles protected-term placeholders ("Globalisa onA
# world"). Default it OFF; rely on the much more reliable GPT rewrite +
# variation + QA passes. Set to True only for legacy comparison tests.
USE_LOCAL_HUMANIZER = False

# If paraphrase word count falls below this ratio vs source, run a length-recovery GPT pass.
MIN_OUTPUT_LENGTH_RATIO = 0.88


def lengthen_output_if_needed(
    pipeline: HumanizationPipeline,
    reference_text: str,
    draft: str,
    tone: str,
    min_ratio: float = MIN_OUTPUT_LENGTH_RATIO,
) -> str:
    """
    Recover detail when the pipeline shortens the document too aggressively
    (feedback: 1900 -> 1471 words).

    Expands only body paragraphs, never touches heading lines.
    """
    ref_w = len(reference_text.split())
    dr_w = len(draft.split())
    if ref_w == 0 or (dr_w / ref_w) >= min_ratio:
        return draft

    from heading_preservation import is_heading_line

    draft_lines = draft.splitlines()
    sections: List[Tuple[List[str], List[str]]] = []
    cur_headings: List[str] = []
    cur_body: List[str] = []

    def flush_section() -> None:
        nonlocal cur_headings, cur_body
        if cur_headings or cur_body:
            sections.append((list(cur_headings), list(cur_body)))
        cur_headings = []
        cur_body = []

    for ln in draft_lines:
        stripped = ln.strip()
        if is_heading_line(ln) or (stripped and heading_word_count(ln) <= 6 and not stripped.endswith(".")):
            if cur_body:
                flush_section()
            cur_headings.append(ln)
        else:
            cur_body.append(ln)
    flush_section()

    expanded_parts: List[str] = []
    for headings, body in sections:
        if headings:
            expanded_parts.extend(headings)
        body_text = "\n".join(body).strip()
        if not body_text or len(body_text.split()) < 30:
            if body_text:
                expanded_parts.append(body_text)
            continue
        try:
            resp = pipeline.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Expand this paragraph to be slightly longer and more detailed. "
                            "Add nuance and qualifiers without inventing new facts or citations. "
                            "Keep the same paragraph breaks and sentence structure. "
                            "Do not add headings, titles, or markdown. "
                            + tone_instruction(tone)
                        ),
                    },
                    {"role": "user", "content": body_text[:6000]},
                ],
                temperature=0.35,
            )
            expanded = (resp.choices[0].message.content or "").strip()
            if expanded and len(expanded.split()) >= len(body_text.split()) * 0.9:
                expanded_parts.append(expanded)
            else:
                expanded_parts.append(body_text)
        except Exception:
            expanded_parts.append(body_text)

    return "\n\n".join(p for p in expanded_parts if p.strip())


_CITE_PLACEHOLDER_RE = re.compile(r"__PRESERVE_CITE_(\d+)__")


def _citation_signature(text: str) -> Tuple[List[int], Dict[int, int]]:
    """Return the ordered list and frequency map of citation placeholder ids."""
    ids = [int(m.group(1)) for m in _CITE_PLACEHOLDER_RE.finditer(text)]
    freq: Dict[int, int] = {}
    for cid in ids:
        freq[cid] = freq.get(cid, 0) + 1
    return ids, freq


def _citation_per_sentence_map(text: str) -> Dict[int, int]:
    """
    Map each citation id to the sentence index it belongs to in *text*.
    Sentences are split on .!? followed by whitespace.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    mapping: Dict[int, int] = {}
    for s_idx, sent in enumerate(sentences):
        for m in _CITE_PLACEHOLDER_RE.finditer(sent):
            mapping[int(m.group(1))] = s_idx
    return mapping


def verify_citation_anchoring(source: str, paraphrased: str) -> Tuple[bool, str]:
    """
    Confirm every __PRESERVE_CITE_X__ from the source still exists in the
    paraphrased output exactly once, in the same document order, and was not
    collapsed into a different sentence.

    Returns (ok, reason). ok=True means safe to keep paraphrased text.
    ok=False means caller should fall back / retry.

    Checks performed:
      1. Same FREQUENCY of every placeholder id (no dropped, no duplicated).
      2. Same DOCUMENT-ORDER of placeholder ids (no reordering).
      3. Citations are not COLLAPSED: the number of distinct sentences that
         contain at least one citation in the output must be >= 70 % of
         the source — anything smaller means citations got merged into a
         single run-on sentence.
    """
    src_ids, src_freq = _citation_signature(source)
    out_ids, out_freq = _citation_signature(paraphrased)

    # 1) Frequency / set check.
    if src_freq != out_freq:
        missing = set(src_freq) - set(out_freq)
        extra = set(out_freq) - set(src_freq)
        if missing:
            return False, f"citations missing in paraphrase: {sorted(missing)}"
        if extra:
            return False, f"unexpected citation ids in paraphrase: {sorted(extra)}"
        return False, "citation frequency mismatch"

    # 2) Document-order check.
    if src_ids != out_ids:
        return False, "citation order changed across sentences"

    # 3) Sentence-spread check (collapse detection).
    src_sent = _citation_per_sentence_map(source)
    out_sent = _citation_per_sentence_map(paraphrased)
    src_sentence_count = len(set(src_sent.values()))
    out_sentence_count = len(set(out_sent.values()))
    if src_sentence_count >= 2 and out_sentence_count < max(2, int(src_sentence_count * 0.7)):
        return (
            False,
            f"citations collapsed into too few sentences "
            f"({out_sentence_count} of {src_sentence_count})",
        )

    return True, "ok"


def rewrite_with_tone(
    pipeline: HumanizationPipeline,
    text: str,
    tone: str,
    humanization_level: str
) -> str:
    """
    GPT rewrite with strict prompt + citation-anchoring verification.

    Up to 2 retries on citation drift; if still unsafe, fall back to the
    original text so a citation is NEVER lost or repositioned.
    """
    src_ids, _ = _citation_signature(text)

    def _call(extra_emphasis: str = "") -> str:
        sys_prompt = _rewrite_system_instructions(tone, humanization_level)
        if extra_emphasis:
            sys_prompt += "\n" + extra_emphasis
        response = pipeline.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text},
            ],
            temperature=humanization_temperature(humanization_level),
        )
        return response.choices[0].message.content or ""

    candidate = _call()
    if not src_ids:
        return candidate

    ok, reason = verify_citation_anchoring(text, candidate)
    if ok:
        return candidate

    # Retry once with stronger emphasis on placeholder integrity.
    retry_msg = (
        "STRICT REPAIR: in your previous attempt the citation anchoring was "
        f"violated ({reason}). EVERY __PRESERVE_CITE_<N>__ token from the "
        "input MUST appear EXACTLY ONCE in the output, in the SAME relative "
        "order, and MUST stay in the SAME sentence as the claim it supports. "
        "Do not delete, duplicate, merge, or move any __PRESERVE_CITE_<N>__ "
        "token. If you cannot satisfy this, return the input unchanged."
    )
    candidate2 = _call(retry_msg)
    ok2, _ = verify_citation_anchoring(text, candidate2)
    if ok2:
        return candidate2

    # Last resort: keep the source text so the citation is never repositioned.
    print(f"[citation-anchor] fallback to source ({reason})")
    return text


def inner_words_per_pass(level: str) -> int:
    if level == "easy":
        return 180
    if level == "hard":
        return 120
    return 150


def split_by_words(text: str, words_per_part: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    parts: List[str] = []
    for start in range(0, len(words), words_per_part):
        parts.append(" ".join(words[start:start + words_per_part]))
    return parts


def looks_degenerate(text: str) -> bool:
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return False

    # Detect runs of the same token repeated (client feedback: tripled phrases).
    run = 1
    for i in range(1, len(words)):
        if words[i] == words[i - 1]:
            run += 1
            if run >= 3:
                return True
        else:
            run = 1

    if len(words) < 30:
        return False

    unique_ratio = len(set(words)) / max(1, len(words))
    if unique_ratio < 0.33:
        return True

    return False


def _humanize_and_grammar_preserving(pipeline: HumanizationPipeline, text: str) -> str:
    """
    Run local humanizer on spans that are not frozen placeholders.

    Both the local humanizer (T5) and local grammar-fix (T5) are OFF by default
    after client feedback (Apr 2026): the humanizer fabricated phrases like
    "rare and omniscient skill" / "Green Energy Management system" and split
    placeholder underscores producing "Globalisa onA"; the grammar model
    introduced typos like "atattracting" / "6wC".  When both are off, the
    GPT rewrite from rewrite_with_tone() is the source of variation, and we
    simply pass the placeholder-aware text through unchanged.
    """
    if not text:
        return text
    if not USE_LOCAL_HUMANIZER and not USE_LOCAL_GRAMMAR_FIX:
        return text
    parts = _INLINE_SPLIT.split(text)
    out: List[str] = []
    for piece in parts:
        if piece == "":
            continue
        core = piece.strip()
        if core and _INLINE_PLACEHOLDER.fullmatch(core):
            out.append(core)
            continue
        if not core:
            out.append(piece)
            continue
        pw = len(piece.split())
        candidate = piece
        if USE_LOCAL_HUMANIZER:
            candidate = pipeline.humanize(piece)
        if USE_LOCAL_GRAMMAR_FIX:
            candidate = pipeline.grammar_fix(candidate)
        if looks_degenerate(candidate):
            candidate = piece
        elif pw > 20 and len(candidate.split()) < pw * 0.55:
            candidate = piece
        if looks_degenerate(candidate):
            candidate = piece
        out.append(candidate)
    return "".join(out)


def _peel_leading_headings_from_body(
    pipeline: HumanizationPipeline,
    body: str,
    tone: str,
) -> Tuple[str, List[str], bool]:
    """
    If the body still starts with heading lines (placeholders missed, or chunk boundary),
    peel them: <=4 words preserved, >4 humanized. wide_gap=True when any long heading
    was peeled so output is clearly separated from the following paragraph.
    """
    lines = body.splitlines()
    idx = 0
    prefix: List[str] = []
    wide_gap = False
    while idx < len(lines):
        if not lines[idx].strip():
            break
        role = heading_peel_role(lines[idx], idx, lines)
        if role is None:
            break
        raw = lines[idx].rstrip("\r\n")
        if role == "preserve":
            prefix.append(raw.strip())
        else:
            wide_gap = True
            prefix.append(rewrite_long_heading(pipeline, raw, tone))
        idx += 1
    rest = "\n".join(lines[idx:]).strip()
    return rest, prefix, wide_gap


def _process_body_segment(
    pipeline: HumanizationPipeline,
    body: str,
    tone: str,
    humanization_level: str,
    protected_map: Dict[str, str],
) -> str:
    body = body.strip()
    if not body:
        return ""

    rest_body, peeled_headings, peeled_wide_gap = _peel_leading_headings_from_body(
        pipeline, body, tone
    )
    if peeled_headings:
        if not rest_body.strip():
            return "\n".join(peeled_headings).strip()
        body = rest_body.strip()

    protected_body = apply_protection(body, protected_map)
    step1 = rewrite_with_tone(pipeline, protected_body, tone, humanization_level)
    inner_n = inner_words_per_pass(humanization_level)
    paragraphs = re.split(r"\n\s*\n+", step1.strip())
    processed_paragraphs: List[str] = []
    for para in paragraphs:
        p = para.strip()
        if not p:
            continue
        sub_parts = split_by_words(p, inner_n)
        processed_parts = [
            _humanize_and_grammar_preserving(pipeline, part) for part in sub_parts
        ]
        processed_paragraphs.append(" ".join(processed_parts).strip())
    merged = "\n\n".join(processed_paragraphs).strip()
    merged = restore_protection(merged, protected_map)
    if peeled_headings:
        head_block = "\n".join(peeled_headings)
        if not merged:
            return head_block
        gap = "\n\n"
        if peeled_wide_gap:
            gap = "\n\n\n"
        return head_block + gap + merged
    return merged


def _split_chunk_by_heading_markers(chunk_text: str) -> List[Tuple[str, str]]:
    """
    Returns ordered list of (segment_kind, text).
    segment_kind: 'preserve' | 'long_heading' | 'body'
    """
    lines = chunk_text.splitlines()
    segments: List[Tuple[str, str]] = []
    buf: List[str] = []
    mode: Optional[str] = None

    def flush() -> None:
        nonlocal buf, mode
        if not buf or mode is None:
            buf = []
            mode = None
            return
        segments.append((mode, "\n".join(buf)))
        buf = []
        mode = None

    for line in lines:
        line = line.replace("\r", "")
        if _FROZEN_HEADING_LINE.match(line):
            if mode != "preserve":
                flush()
                mode = "preserve"
            buf.append(line.strip())
        elif _LONG_HEADING_LINE.match(line):
            if mode != "long_heading":
                flush()
                mode = "long_heading"
            buf.append(line.strip())
        else:
            if mode != "body":
                flush()
                mode = "body"
            buf.append(line)
    flush()
    return segments


def process_chunks(
    pipeline: HumanizationPipeline,
    chunks: List[Chunk],
    tone: str,
    humanization_level: str,
    protected_terms: List[str],
    long_heading_map: Dict[str, str],
) -> str:
    protected_map = build_protected_map(protected_terms)
    final_chunks: List[str] = []
    last_was_heading = False

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i + 1}/{len(chunks)}")

        segments = _split_chunk_by_heading_markers(chunk.text)
        piece_out: List[str] = []

        for seg_kind, seg_text in segments:
            if seg_kind == "preserve":
                # Blank line BEFORE preserved heading (if not first item)
                if piece_out:
                    piece_out.append("")
                piece_out.append(seg_text)
                last_was_heading = True
                continue

            if seg_kind == "long_heading":
                enhanced_lines: List[str] = []
                for ln in seg_text.splitlines():
                    ln_clean = ln.replace("\r", "")
                    core = ln_clean.strip()
                    if _LONG_HEADING_LINE.match(ln_clean):
                        original = long_heading_map.get(core, core)
                        rewritten = rewrite_long_heading(pipeline, original, tone)
                        print(f"  [Long heading] {original[:60]}... -> {rewritten[:60]}...")
                        enhanced_lines.append(rewritten)
                    else:
                        enhanced_lines.append(ln_clean)
                # Blank line BEFORE long heading (if not first item)
                if piece_out:
                    piece_out.append("")
                piece_out.append("\n".join(enhanced_lines))
                last_was_heading = True
                continue

            # body segment
            if last_was_heading and seg_text.strip():
                piece_out.append("")
                last_was_heading = False

            body_result = _process_body_segment(
                pipeline, seg_text, tone, humanization_level, protected_map
            )
            if body_result.strip():
                piece_out.append(body_result)
                last_was_heading = False

        merged_chunk = "\n".join(piece_out).strip()
        final_chunks.append(merged_chunk)

    return "\n\n".join(final_chunks)


def final_qa_pass(text: str) -> str:
    """
    Deterministic, post-restoration QA cleanup applied right before delivery.
    Catches the residual issues flagged by the QA team's PDF that survived
    the model passes:

      * "and.(Author, Year)"        → "and (Author, Year)"
      * "thought.(Author, Year)"    → "thought (Author, Year)"
      * "word(Author, Year)"        → "word (Author, Year)"
      * sentence ending with " ."   → "."
      * doubled punctuation ("..", "?.", "!.", ",,")
      * stray broken placeholder remnants (e.g. "_ _ PROTECTED _ TERM _ 0 _ _")
      * accidental "X of this X"    → "this X"
      * accidental repeated word    → single word
      * accidental "and , and"      → ", and"

    NO model call here — purely text rules so we can never fabricate.
    """
    if not text:
        return text

    text = repair_broken_placeholders(text)
    text = collapse_redundant_phrases(text)

    text = re.sub(
        r"\b(and|but|or|so|yet|nor|while|whereas|although|because|where|when|that|which)\s*[.,;:]\s*\(",
        r"\1 (",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"([A-Za-z0-9])\s*[.,;:]\s*\(([A-Z][^)]*\d{4}[^)]*)\)", r"\1 (\2)", text)
    text = re.sub(r"([A-Za-z0-9])\(", r"\1 (", text)
    text = re.sub(r"\)([A-Za-z])", r") \1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)

    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"([.!?,;:]){2,}", r"\1", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    text = normalise_whitespace(text)
    return text


# ── Patchwriting / similarity detector ───────────────────────────────────────

def _ngrams(words: List[str], n: int) -> set:
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)} if len(words) >= n else set()


def patchwriting_score(source: str, paraphrase: str) -> float:
    """
    Estimate how close the paraphrase is to the source via 5-gram overlap.

    Returns a value in [0, 1] — higher = more similar to source.
    Used to flag patchwriting (client feedback: "minimal synonym changes
    without sufficient structural rewriting").
    """
    if not source or not paraphrase:
        return 0.0
    src_words = re.findall(r"[A-Za-z]+", source.lower())
    out_words = re.findall(r"[A-Za-z]+", paraphrase.lower())
    src_ng = _ngrams(src_words, 5)
    out_ng = _ngrams(out_words, 5)
    if not src_ng or not out_ng:
        return 0.0
    overlap = len(src_ng & out_ng)
    return overlap / max(1, len(src_ng))


def _years_in(text: str) -> set:
    return set(re.findall(r"\b(?:19|20)\d{2}\b", text or ""))


def _numbers_in(text: str) -> set:
    return set(re.findall(r"\b\d{1,3}(?:[.,]\d+)?\b", text or ""))


def gpt_final_qa_pass(
    pipeline: HumanizationPipeline,
    source_text: str,
    draft: str,
    tone: str,
) -> str:
    """
    LLM-based Final Quality Assurance Layer (client request, Apr 2026).

    Reads the paraphrased draft and corrects ONLY:
      • grammar
      • punctuation
      • run-on / fragmented sentences
      • formal academic tone
      • redundancy / awkward phrasing

    Strict guards reject the QA output if it would:
      • drop or add a year
      • drop a parenthetical citation that existed in the draft
      • shrink the word count below 92 % of the draft
      • introduce more than 5 new numeric tokens (proxy for fabrication)

    On rejection or any error, the original draft is returned unchanged so
    the QA layer can never make things worse.
    """
    if not draft or not draft.strip():
        return draft

    system = (
        "You are an academic copy-editor. The user will give you a paraphrased "
        "academic passage. Your job is to perform a FINAL QUALITY-ASSURANCE "
        "edit. " + tone_instruction(tone) + "\n"
        "ONLY do these:\n"
        "  • fix grammar, punctuation and capitalisation\n"
        "  • split run-on sentences and join fragments where appropriate\n"
        "  • smooth awkward phrasing and remove redundancy\n"
        "  • normalise spacing (no '  ', no ' .', no '..', no ',,')\n"
        "  • ensure citations follow standard academic format: a citation at "
        "the end of a sentence is followed by a period AFTER the closing "
        "parenthesis ('claim (Smith, 2020).') — never 'and.(' or 'word.('.\n"
        "DO NOT:\n"
        "  • change the meaning of any sentence\n"
        "  • add new claims, examples, frameworks, names or terms\n"
        "  • remove or move any in-text citation, year, name or number\n"
        "  • shorten the passage materially (stay within 95–105 % of the "
        "input length)\n"
        "  • insert markdown, bullet points or headings\n"
        "  • change numbers, percentages, dates, statistics or proper nouns\n"
        "Output ONLY the corrected passage — no preamble, no commentary."
    )

    try:
        resp = pipeline.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": draft[:12000]},
            ],
            temperature=0.2,
        )
        cleaned = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"[gpt_final_qa_pass] error: {exc!r}; keeping draft")
        return draft

    if not cleaned:
        return draft

    draft_w = len(draft.split())
    out_w = len(cleaned.split())
    if draft_w == 0 or out_w / draft_w < 0.92:
        print(f"[gpt_final_qa_pass] rejected: shrunk {draft_w}->{out_w}; keeping draft")
        return draft

    draft_years = _years_in(draft)
    cleaned_years = _years_in(cleaned)
    if draft_years - cleaned_years:
        print(
            f"[gpt_final_qa_pass] rejected: years dropped "
            f"{sorted(draft_years - cleaned_years)}; keeping draft"
        )
        return draft

    new_numbers = _numbers_in(cleaned) - _numbers_in(draft) - cleaned_years
    if len(new_numbers) > 5:
        print(
            f"[gpt_final_qa_pass] rejected: {len(new_numbers)} new numeric "
            f"tokens introduced; keeping draft"
        )
        return draft

    draft_cites = re.findall(r"\([^()]*\b(?:19|20)\d{2}\b[^()]*\)", draft)
    cleaned_cites = re.findall(r"\([^()]*\b(?:19|20)\d{2}\b[^()]*\)", cleaned)
    if len(cleaned_cites) < len(draft_cites):
        print(
            f"[gpt_final_qa_pass] rejected: citations lost "
            f"({len(draft_cites)}->{len(cleaned_cites)}); keeping draft"
        )
        return draft

    if looks_degenerate(cleaned):
        print("[gpt_final_qa_pass] rejected: degenerate output; keeping draft")
        return draft

    sim = patchwriting_score(source_text, cleaned)
    if sim > 0.85:
        print(f"[gpt_final_qa_pass] warning: high source similarity ({sim:.2f})")

    return cleaned


def get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        return api_key

    print("")
    print("OPENAI_API_KEY is not set in environment.")
    entered = getpass.getpass("Enter your OpenAI API key: ").strip()
    if not entered:
        raise ValueError("OpenAI API key is required.")
    return entered


if __name__ == "__main__":
    print("=" * 60)
    print("   Academic Paraphrasing - Unified Pipeline")
    print("=" * 60)

    tone = select_tone()
    humanization_level = select_humanization_level()
    manual_terms = collect_manual_protected_terms()

    print("")
    print("Step 4: Provide your text.")
    print("Tips: Use <term>...</term> for extra protected phrases. Citations in parentheses, ")
    print("      Author (Year) patterns, and 'Defined Term (ACRONYM)' are auto-preserved.")
    raw_text = get_text_from_user()

    text, xml_terms = parse_xml_protected_terms(raw_text)
    length_reference_text = re.sub(r"\s+", " ", text).strip()
    source_had_markdown = source_uses_markdown_headings(raw_text)
    all_protected_terms = build_safelist_terms(manual_terms + xml_terms)

    text, cite_map = apply_citation_placeholders(text)
    text, acronym_map = apply_acronym_placeholders(text)
    text, heading_map, long_heading_map = apply_heading_placeholders(text)

    print("-" * 60)
    chunks = chunk_text(text)
    if not chunks:
        print("No text to process.")
        raise SystemExit(1)

    api_key = get_openai_api_key()
    pipeline = HumanizationPipeline(api_key)

    result = process_chunks(
        pipeline=pipeline,
        chunks=chunks,
        tone=tone,
        humanization_level=humanization_level,
        protected_terms=all_protected_terms,
        long_heading_map=long_heading_map,
    )
    result = restore_acronym_placeholders(result, acronym_map)
    result = restore_citation_placeholders(result, cite_map)
    result = restore_heading_placeholders(result, heading_map)
    result = dedupe_adjacent_years(result)
    result = sanitize_artifacts(result)
    result = strip_spurious_markdown(result, source_had_markdown)
    result = collapse_stutter_repetition(result)
    result = collapse_redundant_phrases(result)
    result = strip_paraphraser_tag(result)
    result = lengthen_output_if_needed(pipeline, length_reference_text, result, tone)
    result = final_qa_pass(result)
    result = gpt_final_qa_pass(pipeline, length_reference_text, result, tone)
    result = final_qa_pass(result)
    result = normalise_whitespace(result)

    _patch_score = patchwriting_score(length_reference_text, result)
    if _patch_score > 0.85:
        print(
            f"  [patchwriting] WARNING: 5-gram source overlap = "
            f"{_patch_score:.2%} (consider running on 'hard' mode)"
        )

    _src_w = len(length_reference_text.split())
    _out_w = len(result.split())
    _ratio = (_out_w / _src_w) if _src_w else 1.0

    print("=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print("  Tone:                " + tone)
    print("  Humanization level:  " + humanization_level)
    print("  Protected terms:     " + str(all_protected_terms or "None"))
    print("  Total chunks:        " + str(len(chunks)))
    print(f"  Word count:          source ~{_src_w}  output ~{_out_w}  (~{_ratio:.0%} of source)")
    print("=" * 60)
    print("")
    print("FINAL TEXT:")
    print(result)
