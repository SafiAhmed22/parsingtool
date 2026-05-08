import { MIN_HUMANIZATION, MAX_HUMANIZATION } from "../constants";
import { getSliderBackground, getStrengthLabel } from "../utils";
import { useAnimateIn } from "../hooks/useAnimateIn";
import ToneSelector from "./ToneSelector";
import ProtectedTermsInput from "./ProtectedTermsInput";
import type { Tone } from "../types";

interface ControlsPanelProps {
  tone: Tone;
  onToneChange: (tone: Tone) => void;
  protectedTerms: string[];
  onProtectedTermsChange: (terms: string[]) => void;
  humanizationStrength: number;
  onHumanizationChange: (value: number) => void;
  onParaphrase: () => void;
  isParaphrasing: boolean;
  canParaphrase: boolean;
}

const TOTAL_TICKS = 30;

export default function ControlsPanel({
  tone,
  onToneChange,
  protectedTerms,
  onProtectedTermsChange,
  humanizationStrength,
  onHumanizationChange,
  onParaphrase,
  isParaphrasing,
  canParaphrase,
}: ControlsPanelProps) {
  const anim = useAnimateIn(200);
  const strengthLabel = getStrengthLabel(humanizationStrength);
  const thumbPct =
    ((humanizationStrength - MIN_HUMANIZATION) /
      (MAX_HUMANIZATION - MIN_HUMANIZATION)) *
    100;

  return (
    <div ref={anim.ref} className={`animate-in ${anim.visible ? "visible" : ""} max-w-4xl mx-auto w-full`}>
      <section className="card card-accent rounded-2xl p-6 sm:p-8 lg:p-10">
        <div className="flex flex-col gap-7 lg:gap-8">
          {/* Row 1 */}
          <div className="flex flex-col lg:flex-row gap-6 lg:gap-8">
            <div className="lg:w-72">
              <label className="font-display block text-[13px] font-bold text-slate-800 mb-2.5 tracking-wide">
                Tone Selector
              </label>
              <ToneSelector value={tone} onChange={onToneChange} />
            </div>

            <div className="flex-1">
              <label className="font-display block text-[13px] font-bold text-slate-800 mb-2.5 tracking-wide">
                Protected Terms
              </label>
              <ProtectedTermsInput
                terms={protectedTerms}
                onTermsChange={onProtectedTermsChange}
              />
            </div>
          </div>

          <div className="border-t border-slate-100" />

          {/* Row 2 */}
          <div className="flex flex-col lg:flex-row lg:items-end gap-6 lg:gap-10">
            <div className="flex-1">
              <label className="font-display block text-[13px] font-bold text-slate-800 mb-5 tracking-wide">
                Humanization Strength
              </label>

              <div className="relative pb-11">
                <input
                  type="range"
                  min={MIN_HUMANIZATION}
                  max={MAX_HUMANIZATION}
                  value={humanizationStrength}
                  onChange={(e) => onHumanizationChange(Number(e.target.value))}
                  style={{
                    background: getSliderBackground(humanizationStrength, MIN_HUMANIZATION, MAX_HUMANIZATION),
                  }}
                  className="w-full"
                />

                <div className="flex justify-between mt-2 px-[1px]">
                  {Array.from({ length: TOTAL_TICKS }, (_, i) => (
                    <div
                      key={i}
                      className={`w-px transition-all duration-300 ${
                        i % 3 === 0 ? "h-3.5" : "h-2"
                      } ${
                        i / (TOTAL_TICKS - 1) <= thumbPct / 100
                          ? "bg-[#3d6b5e]/50"
                          : "bg-slate-300"
                      }`}
                    />
                  ))}
                </div>

                <div
                  className="absolute bottom-0 -translate-x-1/2 flex flex-col items-center transition-all duration-200 ease-out"
                  style={{ left: `${thumbPct}%` }}
                >
                  <div className="w-0 h-0 border-l-[7px] border-r-[7px] border-b-[7px] border-l-transparent border-r-transparent border-b-[#1a3f36]" />
                  <div className="px-4 py-1.5 rounded-lg bg-[#1a3f36] text-white text-[13px] font-bold shadow-lg shadow-[#1a3f36]/20 transition-transform duration-200">
                    {strengthLabel}
                  </div>
                </div>
              </div>
            </div>

            <div className="shrink-0 lg:pb-11">
              <button
                onClick={onParaphrase}
                disabled={!canParaphrase || isParaphrasing}
                className="group relative w-full lg:w-auto px-12 py-4 bg-gradient-to-r from-[#2d6a4f] to-[#40916c] gradient-animate text-white font-display text-[15px] font-bold rounded-xl shadow-lg shadow-[#2d6a4f]/20 transition-all duration-300 hover:shadow-xl hover:shadow-[#2d6a4f]/30 hover:-translate-y-1 active:translate-y-0 active:shadow-md disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-lg flex items-center justify-center gap-3 overflow-hidden"
              >
                {/* Shine sweep on hover */}
                <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                {isParaphrasing ? (
                  <span className="relative flex items-center gap-3">
                    <svg className="animate-spin w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Paraphrasing…
                  </span>
                ) : (
                  <span className="relative flex items-center gap-3">
                    <svg className="w-[18px] h-[18px] transition-transform duration-500 group-hover:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Paraphrase
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
