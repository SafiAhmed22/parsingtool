"""
Chunking Engine for Academic Paraphrasing Pipeline
Splits input text into fixed-size chunks for downstream processing.

Strategy:
  1. Accept text from: plain paste, .txt, .pdf, or .docx file
  2. Chunk text into blocks of MAX_WORDS words (last chunk may be shorter)
  3. Ignore paragraph/newline boundaries for chunking
  4. Each chunk carries metadata (index, word count, is_sub_chunk)
"""

import os
from dataclasses import dataclass


MAX_WORDS = 225


@dataclass
class Chunk:
    index: int           # Position in the final chunk sequence
    text: str            # The actual chunk content
    word_count: int      # Word count of this chunk
    is_sub_chunk: bool   # Reserved compatibility flag (always False in fixed mode)


# ── Word Utilities ────────────────────────────────────────────────────────────


def _word_count(text: str) -> int:
    return len(text.split())


# ── Document Extraction ───────────────────────────────────────────────────────

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts plain text from a .pdf, .docx, or .txt file.
    Returns extracted text as a single string.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("Install pypdf: pip install pypdf")
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()

    elif ext == ".docx":
        try:
            from docx import Document
        except ImportError:
            raise ImportError("Install python-docx: pip install python-docx")
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs).strip()

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Use .pdf, .docx, or .txt")


def get_text_from_user() -> str:
    """
    Prompts user to either paste text or provide a file path (.pdf / .docx / .txt).
    Returns extracted plain text string either way.
    """
    print("\nHow would you like to provide your text?")
    print("  1. Paste text directly")
    print("  2. Upload a file  (.pdf / .docx / .txt)")

    while True:
        choice = input("Enter 1 or 2: ").strip()

        if choice == "1":
            print("\nPaste your text below. Type END on a new line when done:\n")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            text = "\n".join(lines).strip()
            if not text:
                print("No text entered. Please try again.")
                continue
            return text

        elif choice == "2":
            file_path = input("\nEnter the full file path: ").strip().strip('"').strip("'")
            if not os.path.exists(file_path):
                print(f"File not found: '{file_path}'. Please try again.")
                continue
            try:
                text = extract_text_from_file(file_path)
                if not text:
                    print("File appears to be empty. Please try again.")
                    continue
                print(f"✓ Extracted {_word_count(text)} words from file.")
                return text
            except Exception as e:
                print(f"Error reading file: {e}. Please try again.")

        else:
            print("Invalid choice. Enter 1 or 2.")


# ── Main Chunking Entry Point ─────────────────────────────────────────────────

def chunk_text(text: str) -> list[Chunk]:
    """
    Split into chunks of roughly MAX_WORDS without breaking line boundaries,
    so headings and paragraph breaks stay intact. A single line longer than
    MAX_WORDS falls back to word-based slicing for that line only.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_words = 0

    def flush_buffer() -> None:
        nonlocal buf, buf_words
        if not buf:
            return
        joined = "\n".join(buf).strip()
        if joined:
            wc = len(joined.split())
            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=joined,
                    word_count=wc,
                    is_sub_chunk=False,
                )
            )
        buf = []
        buf_words = 0

    for line in lines:
        line_words = len(line.split())
        if line_words > MAX_WORDS:
            flush_buffer()
            words = line.split()
            for start in range(0, len(words), MAX_WORDS):
                word_slice = words[start : start + MAX_WORDS]
                piece = " ".join(word_slice)
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        text=piece,
                        word_count=len(word_slice),
                        is_sub_chunk=False,
                    )
                )
            continue

        if buf_words + line_words > MAX_WORDS and buf:
            flush_buffer()

        buf.append(line)
        buf_words += line_words

    flush_buffer()
    return chunks


# -- Entry Point --
if __name__ == "__main__":
    print("=" * 60)
    print("   Academic Paraphrasing - Chunking Engine")
    print("=" * 60)

    # Step 1: Tone
    print("")
    print("Step 1: Select tone:")
    print("  1. phd_academic      - PhD dissertation level")
    print("  2. standard_academic - Graduate / undergraduate level")
    print("  3. esl_simple        - Simple, accessible academic English")
    tone_map = {"1": "phd_academic", "2": "standard_academic", "3": "esl_simple"}
    while True:
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice in tone_map:
            tone = tone_map[choice]
            break
        print("Invalid. Please enter 1, 2, or 3.")

    # Step 2: Protected terms
    print("")
    print("Step 2: Enter protected terms (comma-separated), or press Enter to skip:")
    raw_terms = input().strip()
    protected_terms = [t.strip() for t in raw_terms.split(",") if t.strip()] if raw_terms else []

    # Step 3: Humanization strength
    print("")
    print("Step 3: Humanization strength (1 = minimal, 10 = maximum):")
    while True:
        raw = input("Enter a number from 1 to 10: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= 10:
            humanize_level = int(raw)
            break
        print("Invalid. Please enter a number between 1 and 10.")

    # Step 4: Text input
    print("")
    print("Step 4: Provide your text.")
    text = get_text_from_user()

    # Step 5: Chunk
    print("-" * 60)
    chunks = chunk_text(text)

    # Stop if text was too short
    if not chunks:
        exit(1)

    # Summary
    print("=" * 60)
    print("  CHUNKING COMPLETE")
    print("=" * 60)
    print("  Tone:            " + tone)
    print("  Protected terms: " + str(protected_terms or "None"))
    print("  Humanize level:  " + str(humanize_level) + "/10")
    print("  Total chunks:    " + str(len(chunks)))
    print("=" * 60)
    print("")
    for chunk in chunks:
        print("[Chunk " + str(chunk.index) + "] words=" + str(chunk.word_count) + " sub_chunk=" + str(chunk.is_sub_chunk))
        print("  Preview: " + chunk.text[:100] + "...")
        print("")
