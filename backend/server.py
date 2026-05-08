"""
FastAPI server for the Academic Paraphraser pipeline.
Exposes an SSE endpoint that streams chunk-by-chunk progress in real time.
"""

import os
import re
import json
import queue
import threading
import asyncio
from typing import AsyncGenerator, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _name in (".env", "env"):
    _p = os.path.join(_BASE_DIR, _name)
    if os.path.isfile(_p):
        load_dotenv(_p)
load_dotenv()

from pipeline import HumanizationPipeline
from chunkingengine import chunk_text
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
    restore_heading_placeholders,
)
from main import (
    parse_xml_protected_terms,
    build_protected_map,
    rewrite_long_heading,
    _process_body_segment,
    _split_chunk_by_heading_markers,
    lengthen_output_if_needed,
    final_qa_pass,
    gpt_final_qa_pass,
    patchwriting_score,
    _LONG_HEADING_LINE,
)

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Academic Paraphraser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global pipeline (loaded once at startup) ─────────────────────────────────

pipeline: HumanizationPipeline | None = None


@app.on_event("startup")
def load_models():
    global pipeline
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("[server] WARNING: OPENAI_API_KEY not set — pipeline disabled")
        return
    print("[server] Loading models (this may take a minute on first run)...")
    pipeline = HumanizationPipeline(api_key)
    print("[server] Pipeline ready.")


# ── Tone / humanization mapping ──────────────────────────────────────────────

TONE_MAP: Dict[str, str] = {
    "phd": "phd_academic",
    "standard": "standard_academic",
    "esl": "esl_simple",
}


def _humanization_level(strength: int) -> str:
    if strength <= 3:
        return "easy"
    if strength <= 7:
        return "medium"
    return "hard"


# ── Request schema ───────────────────────────────────────────────────────────

class ParaphraseRequest(BaseModel):
    text: str
    tone: str = "standard"
    protected_terms: list[str] = []
    humanization_strength: int = 7


# ── Core streaming pipeline ─────────────────────────────────────────────────

def _run_pipeline(req: ParaphraseRequest, q: queue.Queue) -> None:
    """
    Runs the full paraphrasing pipeline in a background thread.
    Pushes SSE-ready dicts into *q*; a final ``None`` signals completion.
    """
    try:
        tone = TONE_MAP.get(req.tone, "standard_academic")
        level = _humanization_level(req.humanization_strength)

        def emit(event_type: str, **data):
            q.put({"event": event_type, "data": {**data}})
            print(f"  [SSE] {event_type}: {json.dumps(data)[:120]}")

        emit("status", message="Preparing text…")

        text, xml_terms = parse_xml_protected_terms(req.text)
        length_ref = re.sub(r"\s+", " ", text).strip()
        source_md = source_uses_markdown_headings(req.text)
        all_terms = build_safelist_terms(req.protected_terms + xml_terms)

        text, cite_map = apply_citation_placeholders(text)
        text, acronym_map = apply_acronym_placeholders(text)
        text, heading_map, long_heading_map = apply_heading_placeholders(text)

        chunks = chunk_text(text)
        if not chunks:
            emit("error", message="No processable text found.")
            q.put(None)
            return

        total = len(chunks)
        emit("status", message=f"Found {total} chunk(s). Starting paraphrase…")

        protected_map = build_protected_map(all_terms)
        final_chunks: List[str] = []
        last_was_heading = False

        for i, chunk in enumerate(chunks):
            emit("progress", chunk=i + 1, total=total,
                 message=f"Processing chunk {i + 1}/{total}")

            segments = _split_chunk_by_heading_markers(chunk.text)
            piece_out: List[str] = []

            for seg_kind, seg_text in segments:
                if seg_kind == "preserve":
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
                            emit("heading",
                                 original=original[:100],
                                 rewritten=rewritten[:100])
                            enhanced_lines.append(rewritten)
                        else:
                            enhanced_lines.append(ln_clean)
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
                    pipeline, seg_text, tone, level, protected_map
                )
                if body_result.strip():
                    piece_out.append(body_result)
                    last_was_heading = False

            merged = "\n".join(piece_out).strip()
            # Light per-chunk cleanup so the streamed UI shows polished text
            # immediately. Citation/acronym placeholders are still in place
            # here — final restoration happens after all chunks are joined.
            merged = collapse_redundant_phrases(merged)
            merged = collapse_stutter_repetition(merged)
            final_chunks.append(merged)
            emit("chunk", index=i, text=merged)

        # ── Post-processing ──────────────────────────────────────────────
        emit("status", message="Post-processing…")
        result = "\n\n".join(final_chunks)
        result = restore_acronym_placeholders(result, acronym_map)
        result = restore_citation_placeholders(result, cite_map)
        result = restore_heading_placeholders(result, heading_map)
        result = dedupe_adjacent_years(result)
        result = sanitize_artifacts(result)
        result = strip_spurious_markdown(result, source_md)
        result = collapse_stutter_repetition(result)
        result = collapse_redundant_phrases(result)
        result = strip_paraphraser_tag(result)
        result = lengthen_output_if_needed(pipeline, length_ref, result, tone)
        result = final_qa_pass(result)
        emit("status", message="Running final quality-assurance check…")
        result = gpt_final_qa_pass(pipeline, length_ref, result, tone)
        result = final_qa_pass(result)
        result = normalise_whitespace(result)

        src_w = len(length_ref.split())
        out_w = len(result.split())
        patch = patchwriting_score(length_ref, result)
        emit(
            "complete",
            text=result,
            source_words=src_w,
            output_words=out_w,
            similarity=round(patch, 3),
        )

    except Exception as exc:
        q.put({"event": "error", "data": {"message": str(exc)}})

    finally:
        q.put(None)


# ── SSE endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/paraphrase")
async def paraphrase_sse(req: ParaphraseRequest):
    if pipeline is None:
        async def err():
            yield {
                "event": "error",
                "data": json.dumps({"message": "Pipeline not loaded — check OPENAI_API_KEY"}),
            }
        return EventSourceResponse(err())

    q: queue.Queue = queue.Queue()
    thread = threading.Thread(target=_run_pipeline, args=(req, q), daemon=True)
    thread.start()

    async def event_stream() -> AsyncGenerator[dict, None]:
        while True:
            try:
                item = await asyncio.to_thread(q.get, timeout=300)
            except Exception:
                break
            if item is None:
                break
            yield {
                "event": item["event"],
                "data": json.dumps(item["data"]),
            }

    return EventSourceResponse(event_stream())


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "pipeline_loaded": pipeline is not None,
    }
