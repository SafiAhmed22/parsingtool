import { useState, useCallback, useEffect, useRef } from "react";
import Header from "./components/Header";
import HeroBanner from "./components/HeroBanner";
import ControlsPanel from "./components/ControlsPanel";
import TextPanels from "./components/TextPanels";
import { DEFAULT_HUMANIZATION } from "./constants";
import type { Tone } from "./types";

export default function App() {
  const [originalText, setOriginalText] = useState("");
  const [paraphrasedText, setParaphrasedText] = useState("");
  const [tone, setTone] = useState<Tone>("phd");
  const [protectedTerms, setProtectedTerms] = useState<string[]>([]);
  const [humanizationStrength, setHumanizationStrength] =
    useState(DEFAULT_HUMANIZATION);
  const [isParaphrasing, setIsParaphrasing] = useState(false);
  const [streamStatus, setStreamStatus] = useState("");
  const [streamProgress, setStreamProgress] = useState<{ chunk: number; total: number } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const canParaphrase = originalText.trim().length > 0 && !isParaphrasing;

  const handleParaphrase = useCallback(async () => {
    if (!canParaphrase) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsParaphrasing(true);
    setParaphrasedText("");
    setStreamStatus("Connecting…");
    setStreamProgress(null);

    try {
      const resp = await fetch("/api/paraphrase", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: originalText,
          tone,
          protected_terms: protectedTerms,
          humanization_strength: humanizationStrength,
        }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`Server error: ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6);
            try {
              const data = JSON.parse(raw);
              switch (currentEvent) {
                case "status":
                  setStreamStatus(data.message ?? "");
                  break;
                case "progress":
                  setStreamProgress({ chunk: data.chunk, total: data.total });
                  setStreamStatus(data.message ?? "");
                  break;
                case "chunk":
                  setParaphrasedText((prev) =>
                    prev ? prev + "\n\n" + data.text : data.text
                  );
                  break;
                case "complete":
                  setParaphrasedText(data.text);
                  setStreamStatus("");
                  setStreamProgress(null);
                  break;
                case "error":
                  setParaphrasedText(
                    `Error: ${data.message ?? "Unknown error"}`
                  );
                  break;
              }
            } catch {
              /* skip malformed JSON */
            }
            currentEvent = "";
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setParaphrasedText(
          "An error occurred while paraphrasing. Please check the backend is running and try again."
        );
      }
    } finally {
      setIsParaphrasing(false);
      setStreamStatus("");
      setStreamProgress(null);
    }
  }, [canParaphrase, originalText, tone, protectedTerms, humanizationStrength]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleParaphrase();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleParaphrase]);

  return (
    <div className="min-h-screen bg-white flex flex-col relative overflow-hidden">
      {/* Neon glow orbs */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-40 left-1/4 w-[500px] h-[500px] rounded-full bg-[#2d6a4f]/[0.07] blur-[150px] breathe" />
        <div className="absolute top-1/3 -right-20 w-[400px] h-[400px] rounded-full bg-[#c4704e]/[0.05] blur-[130px] breathe [animation-delay:2s]" />
        <div className="absolute -bottom-32 left-1/2 -translate-x-1/2 w-[600px] h-[400px] rounded-full bg-[#2d6a4f]/[0.04] blur-[140px] breathe [animation-delay:4s]" />
      </div>

      <main className="relative flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-6 sm:py-10 lg:py-12 flex flex-col gap-6 sm:gap-8">
        <Header />
        <HeroBanner />
        <ControlsPanel
          tone={tone}
          onToneChange={setTone}
          protectedTerms={protectedTerms}
          onProtectedTermsChange={setProtectedTerms}
          humanizationStrength={humanizationStrength}
          onHumanizationChange={setHumanizationStrength}
          onParaphrase={handleParaphrase}
          isParaphrasing={isParaphrasing}
          canParaphrase={canParaphrase}
        />
        <TextPanels
          originalText={originalText}
          onOriginalTextChange={setOriginalText}
          paraphrasedText={paraphrasedText}
          isParaphrasing={isParaphrasing}
          streamStatus={streamStatus}
          streamProgress={streamProgress}
        />
      </main>
    </div>
  );
}
