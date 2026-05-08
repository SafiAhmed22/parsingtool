# @title
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

class HumanizationPipeline:

    def __init__(self, openai_api_key):

        # ---------- OpenAI ----------
        self.client = OpenAI(api_key=openai_api_key)

        # ---------- Device ----------
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("Using device:", self.device)

        # ---------- Humanizer ----------
        print("Loading humanizer model (CPU-safe)...")
        self.h_tokenizer = AutoTokenizer.from_pretrained("NoaiGPT/777")
        self.h_model = AutoModelForSeq2SeqLM.from_pretrained(
            "NoaiGPT/777"
        ).to("cpu")  # Force CPU for safety

        # ---------- Grammar Corrector ----------
        print("Loading grammar correction model (CPU-safe)...")
        self.g_tokenizer = AutoTokenizer.from_pretrained("vennify/t5-base-grammar-correction")
        self.g_model = AutoModelForSeq2SeqLM.from_pretrained(
            "vennify/t5-base-grammar-correction"
        ).to("cpu")  # Force CPU for safety

        print("Models loaded successfully")

    # ---------------------------------------
    # Chunk text safely
    # ---------------------------------------
    def chunk_text(self, text, max_words=225):

        words = text.split()
        chunks = []

        for start in range(0, len(words), max_words):
            word_slice = words[start:start + max_words]
            chunks.append(" ".join(word_slice))

        return chunks

    # ---------------------------------------
    # Step 1: GPT-4o-mini rewrite
    # ---------------------------------------
    def rewrite_llm(self, text):

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Rewrite the text in a natural human style while preserving meaning."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    # ---------------------------------------
    # Step 2: Humanize (CPU)
    # ---------------------------------------
    def humanize(self, text):

        formatted = f"paraphraser: {text}"

        inputs = self.h_tokenizer(
            formatted,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )  # CPU-safe, no .to(self.device)

        outputs = self.h_model.generate(
            **inputs,
            do_sample=True,
            temperature=0.72,
            top_p=0.9,
            repetition_penalty=1.18,
            max_length=512
        )

        return self.h_tokenizer.decode(outputs[0], skip_special_tokens=True)

    # ---------------------------------------
    # Step 3: Grammar correction (CPU)
    # ---------------------------------------
    def grammar_fix(self, text):

        prompt = "grammar: " + text

        inputs = self.g_tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )  # CPU-safe, no .to(self.device)

        outputs = self.g_model.generate(
            **inputs,
            max_length=512
        )

        return self.g_tokenizer.decode(outputs[0], skip_special_tokens=True)

    # ---------------------------------------
    # Full pipeline
    # ---------------------------------------
    def process(self, text):

        chunks = self.chunk_text(text)
        final_chunks = []

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")

            step1 = self.rewrite_llm(chunk)
            step2 = self.humanize(step1)
            step3 = self.grammar_fix(step2)

            final_chunks.append(step3)

        return "\n\n".join(final_chunks)


# ---------------------------------------
# Example usage
# ---------------------------------------
if __name__ == "__main__":

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    pipeline = HumanizationPipeline(OPENAI_API_KEY)

    text = """"""
    result = pipeline.process(text)

    print("\nFINAL TEXT:\n")
    print(result)