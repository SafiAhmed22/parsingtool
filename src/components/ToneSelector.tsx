import { useState, useRef, useEffect } from "react";
import { TONE_OPTIONS } from "../constants";
import type { Tone } from "../types";

interface ToneSelectorProps {
  value: Tone;
  onChange: (tone: Tone) => void;
}

export default function ToneSelector({ value, onChange }: ToneSelectorProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = TONE_OPTIONS.find((o) => o.value === value)!;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3 text-[14px] font-semibold text-slate-800 cursor-pointer transition-all duration-200 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#2d6a4f]/10 focus:border-[#40916c]"
      >
        {selected.label}
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-2 w-full bg-white border border-slate-200 rounded-xl shadow-xl shadow-slate-900/10 overflow-hidden animate-fade-in">
          {TONE_OPTIONS.map((opt) => {
            const isActive = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => { onChange(opt.value); setOpen(false); }}
                className={`w-full flex items-center justify-between px-4 py-3.5 text-[14px] transition-colors duration-100 ${
                  isActive
                    ? "bg-[#d4edda] text-[#1a3f36] font-bold"
                    : "text-slate-700 font-medium hover:bg-slate-50"
                }`}
              >
                {opt.label}
                {isActive && (
                  <svg className="w-5 h-5 text-[#2d6a4f]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
