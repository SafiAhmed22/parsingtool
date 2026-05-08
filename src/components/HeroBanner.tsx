import { useAnimateIn } from "../hooks/useAnimateIn";

export default function HeroBanner() {
  const anim = useAnimateIn(100);

  return (
    <div ref={anim.ref} className={`animate-in ${anim.visible ? "visible" : ""} max-w-4xl mx-auto w-full`}>
      <section className="hero-glow relative overflow-hidden rounded-2xl px-6 sm:px-10 lg:px-16 py-7 sm:py-9 text-center">
        {/* Base gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0f1f2e] via-[#162d3e] to-[#0f1f2e]" />

        {/* Animated ambient glow */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#2d6a4f]/20 rounded-full blur-[120px] breathe" />
          <div className="absolute bottom-0 left-0 w-80 h-80 bg-[#c4704e]/10 rounded-full blur-[100px] breathe [animation-delay:1s]" />
          <div className="absolute top-1/4 right-0 w-64 h-64 bg-[#2d6a4f]/10 rounded-full blur-[80px] breathe [animation-delay:2s]" />
        </div>

        {/* Grid overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
          }}
        />

        <div className="relative max-w-2xl mx-auto">
          <h2 className="font-display text-[1.5rem] sm:text-[2rem] lg:text-[2.5rem] font-extrabold leading-[1.15] tracking-[-0.02em] text-white mb-3">
            The Ideal Academic
            <br />
            <span className="shimmer-text">
              Paraphrasing Tool
            </span>
          </h2>

          <p className="text-[0.875rem] sm:text-[1rem] font-semibold text-slate-300 leading-relaxed">
            Focusing on Clarity, Integrity, and Academic Standards
          </p>
        </div>
      </section>
    </div>
  );
}
