import { useState, useRef } from "react";
import { countWords, countChars } from "../utils";
import { useAnimateIn } from "../hooks/useAnimateIn";

const SAMPLE_TEXTS = [
  "The mitochondria, often referred to as the powerhouse of the cell, play a critical role in aerobic respiration by facilitating the conversion of adenosine diphosphate (ADP) into adenosine triphosphate (ATP) through oxidative phosphorylation. This process occurs across the inner mitochondrial membrane, where the electron transport chain establishes a proton gradient essential for ATP synthase activity.",
  "Photosynthesis is a fundamental biochemical process through which autotrophic organisms convert light energy into chemical energy stored in glucose molecules. The light-dependent reactions occur in the thylakoid membranes, generating ATP and NADPH, which subsequently drive the Calvin cycle in the stroma to fix atmospheric carbon dioxide into organic compounds.",
];

interface TextPanelsProps {
  originalText: string;
  onOriginalTextChange: (text: string) => void;
  paraphrasedText: string;
  isParaphrasing: boolean;
  streamStatus?: string;
  streamProgress?: { chunk: number; total: number } | null;
}

export default function TextPanels({
  originalText,
  onOriginalTextChange,
  paraphrasedText,
  isParaphrasing,
  streamStatus = "",
  streamProgress = null,
}: TextPanelsProps) {
  const [copied, setCopied] = useState(false);
  const animLeft = useAnimateIn(300);
  const animRight = useAnimateIn(450);
  const fileRef = useRef<HTMLInputElement>(null);

  const origWords = countWords(originalText);
  const origChars = countChars(originalText);
  const paraWords = countWords(paraphrasedText);
  const paraChars = countChars(paraphrasedText);

  const hasOutput = paraphrasedText.length > 0;
  const isEmpty = originalText.trim().length === 0;

  function handleTrySample() {
    const sample = SAMPLE_TEXTS[Math.floor(Math.random() * SAMPLE_TEXTS.length)];
    onOriginalTextChange(sample);
  }

  async function handlePaste() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) onOriginalTextChange(text);
    } catch {
      /* clipboard access denied — user can paste manually */
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result;
      if (typeof text === "string") onOriginalTextChange(text);
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  async function handleCopy() {
    if (!paraphrasedText) return;
    try {
      await navigator.clipboard.writeText(paraphrasedText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = paraphrasedText;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-5 sm:gap-6">
      {/* Original Text */}
      <div ref={animLeft.ref} className={`animate-in ${animLeft.visible ? "visible" : ""}`}>
        <div className="card card-accent rounded-2xl flex flex-col min-h-[360px] sm:min-h-[480px] overflow-hidden h-full">
          <div className="flex items-center justify-between px-6 sm:px-7 py-5 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-[#40916c] shadow-sm shadow-[#40916c]/30" />
              <h2 className="font-display text-[15px] font-bold text-slate-900">Original text</h2>
            </div>
            <span className="text-[12px] text-slate-400 font-semibold tabular-nums bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100 transition-all duration-300">
              {origWords} {origWords === 1 ? "word" : "words"} · {origChars} {origChars === 1 ? "char" : "chars"}
            </span>
          </div>

          <div className="flex-1 p-5 sm:p-6 flex flex-col">
            {/* Action buttons when empty */}
            {isEmpty && (
              <div className="flex flex-wrap items-center gap-2.5 mb-4 animate-fade-in">
                <button
                  onClick={handleTrySample}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-[13px] font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl transition-all duration-200 hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
                >
                  Try a sample
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </button>
                <button
                  onClick={handlePaste}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-[13px] font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl transition-all duration-200 hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
                >
                  Paste here
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
                <button
                  onClick={() => fileRef.current?.click()}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-[13px] font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl transition-all duration-200 hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
                >
                  Upload file
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </button>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".txt,.doc,.docx,.pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </div>
            )}

            <textarea
              value={originalText}
              onChange={(e) => onOriginalTextChange(e.target.value)}
              placeholder="Paste your academic text here..."
              className="w-full flex-1 min-h-[240px] sm:min-h-[340px] text-[15px] leading-[1.8] text-slate-700 placeholder:text-slate-400 bg-transparent transition-colors duration-200"
              spellCheck={false}
            />
          </div>
        </div>
      </div>

      {/* Paraphrased Output */}
      <div ref={animRight.ref} className={`animate-in ${animRight.visible ? "visible" : ""}`}>
        <div className="card card-accent rounded-2xl flex flex-col min-h-[360px] sm:min-h-[480px] overflow-hidden h-full">
          <div className="flex items-center justify-between px-6 sm:px-7 py-5 border-b border-slate-100 gap-3">
            <div className="flex items-center gap-3 shrink-0">
              <div className="w-3 h-3 rounded-full bg-[#c4704e] shadow-sm shadow-[#c4704e]/30" />
              <h2 className="font-display text-[15px] font-bold text-slate-900">Paraphrased output</h2>
            </div>
            <div className="flex items-center gap-2 flex-wrap justify-end">
              <span className="text-[12px] text-slate-400 font-semibold tabular-nums bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100 hidden sm:inline transition-all duration-300">
                {paraWords} {paraWords === 1 ? "word" : "words"} · {paraChars} {paraChars === 1 ? "char" : "chars"}
              </span>
              <button
                onClick={handleCopy}
                disabled={!hasOutput}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-[12px] font-bold rounded-lg bg-white border border-slate-200 text-slate-600 transition-all duration-200 hover:bg-[#e8f5ef] hover:border-[#c7e5d6] hover:text-[#2d6a4f] hover:shadow-md disabled:opacity-25 disabled:cursor-not-allowed active:scale-95 shadow-sm"
              >
                {copied ? (
                  <>
                    <svg className="w-3.5 h-3.5 text-[#2d6a4f]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  if (!paraphrasedText) return;
                  const blob = new Blob([paraphrasedText], { type: "text/plain" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "paraphrased-output.txt";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                disabled={!hasOutput}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-[12px] font-bold rounded-lg bg-white border border-slate-200 text-slate-600 transition-all duration-200 hover:bg-[#e8f5ef] hover:border-[#c7e5d6] hover:text-[#2d6a4f] hover:shadow-md disabled:opacity-25 disabled:cursor-not-allowed active:scale-95 shadow-sm"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                .txt
              </button>
            </div>
          </div>

          <div className="flex-1 p-5 sm:p-6 relative">
            {isParaphrasing && !hasOutput ? (
              <div className="flex flex-col items-center justify-center h-full gap-5 animate-fade-in">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full bg-[#40916c] opacity-10 animate-ping" />
                  <div className="absolute inset-1 rounded-full bg-[#40916c] opacity-5 animate-ping [animation-delay:200ms]" />
                  <div className="relative w-16 h-16 rounded-full bg-[#e8f5ef] border border-[#c7e5d6] flex items-center justify-center">
                    <svg className="animate-spin w-7 h-7 text-[#2d6a4f]" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                </div>
                <div className="text-center">
                  <p className="font-display text-[15px] font-bold text-slate-800">
                    {streamStatus || "Generating paraphrase…"}
                  </p>
                  {streamProgress && (
                    <div className="mt-3 w-48 mx-auto">
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[#40916c] to-[#2d6a4f] rounded-full transition-all duration-500"
                          style={{ width: `${(streamProgress.chunk / streamProgress.total) * 100}%` }}
                        />
                      </div>
                      <p className="text-[12px] text-slate-400 mt-1.5 tabular-nums">
                        Chunk {streamProgress.chunk} of {streamProgress.total}
                      </p>
                    </div>
                  )}
                  {!streamProgress && (
                    <p className="text-[13px] text-slate-400 mt-1.5">Humanizing your academic text</p>
                  )}
                </div>
              </div>
            ) : isParaphrasing && hasOutput ? (
              <div className="flex-1 flex flex-col">
                <div className="text-[15px] leading-[1.8] text-slate-700 whitespace-pre-wrap flex-1 overflow-y-auto">
                  {paraphrasedText}
                </div>
                {streamProgress && (
                  <div className="pt-4 mt-4 border-t border-slate-100">
                    <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#40916c] to-[#2d6a4f] rounded-full transition-all duration-700 ease-out"
                        style={{ width: `${Math.round((streamProgress.chunk / streamProgress.total) * 100)}%` }}
                      />
                    </div>
                    <p className="text-[13px] text-slate-600 font-semibold mt-2 tabular-nums">
                      Processing… {Math.round((streamProgress.chunk / streamProgress.total) * 100)}% Complete
                    </p>
                  </div>
                )}
              </div>
            ) : hasOutput ? (
              <div className="text-[15px] leading-[1.8] text-slate-700 whitespace-pre-wrap animate-fade-in">
                {paraphrasedText}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
                <div className="w-16 h-16 rounded-2xl bg-[#fff3ed] border border-[#f5d5c3] flex items-center justify-center animate-float">
                  <svg className="w-7 h-7 text-[#c4704e]" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM12 17c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zM9 8V6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9z" />
                  </svg>
                </div>
                <div>
                  <p className="font-display text-[15px] font-bold text-slate-500">Awaiting generation…</p>
                  <p className="text-[13px] text-slate-400 mt-1.5">Paste text and click Paraphrase to begin</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
