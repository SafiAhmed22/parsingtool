import { useState, useRef, type KeyboardEvent } from "react";

const PLACEHOLDER_TERMS = ["Photosynthesis", "Chlorophyll"];

interface ProtectedTermsInputProps {
  terms: string[];
  onTermsChange: (terms: string[]) => void;
}

export default function ProtectedTermsInput({ terms, onTermsChange }: ProtectedTermsInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const showPlaceholders = terms.length === 0 && !inputValue && !focused;

  function addTerm(raw: string) {
    const term = raw.trim();
    if (!term) return;
    if (terms.some((t) => t.toLowerCase() === term.toLowerCase())) return;
    onTermsChange([...terms, term]);
    setInputValue("");
  }

  function removeTerm(index: number) {
    onTermsChange(terms.filter((_, i) => i !== index));
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTerm(inputValue);
    }
    if (e.key === "Backspace" && !inputValue && terms.length > 0) {
      removeTerm(terms.length - 1);
    }
  }

  function handleFocus() {
    setFocused(true);
  }

  function handleBlur() {
    if (inputValue.trim()) addTerm(inputValue);
    if (terms.length === 0 && !inputValue.trim()) setFocused(false);
  }

  return (
    <div
      onClick={() => { inputRef.current?.focus(); }}
      className="flex flex-wrap items-center gap-2 min-h-[46px] bg-white border border-slate-200 rounded-xl px-3 py-2 cursor-text transition-all duration-200 hover:border-slate-300 focus-within:border-teal-400 focus-within:ring-2 focus-within:ring-teal-500/10"
    >
      {/* Placeholder example tags */}
      {showPlaceholders && (
        <>
          {PLACEHOLDER_TERMS.map((term) => (
            <span
              key={term}
              className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold bg-[#e8997a]/60 text-white/80"
            >
              {term}
            </span>
          ))}
          <span className="text-xs text-slate-400 font-medium">etc.</span>
        </>
      )}

      {/* Real tags */}
      {terms.map((term, i) => (
        <span
          key={`${term}-${i}`}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-[#e8997a] text-white shadow-sm animate-fade-in"
        >
          {term}
          <button
            onClick={(e) => { e.stopPropagation(); removeTerm(i); }}
            className="w-4 h-4 rounded-full inline-flex items-center justify-center transition-colors hover:bg-white/25"
            aria-label={`Remove ${term}`}
          >
            <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}

      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={!showPlaceholders && terms.length === 0 ? "Type a term and press Enter…" : ""}
        className={`flex-1 min-w-[140px] bg-transparent text-sm text-slate-800 placeholder:text-slate-400 outline-none py-1 ${showPlaceholders ? "absolute opacity-0" : ""}`}
      />
    </div>
  );
}
