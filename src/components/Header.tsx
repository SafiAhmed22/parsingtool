import { useAnimateIn } from "../hooks/useAnimateIn";

export default function Header() {
  const anim = useAnimateIn(0);

  return (
    <div ref={anim.ref} className={`animate-in ${anim.visible ? "visible" : ""}`}>
      <header className="card rounded-2xl px-6 sm:px-10 py-5 sm:py-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-br from-[#2d6a4f] to-[#40916c] gradient-animate flex items-center justify-center shadow-lg shadow-[#2d6a4f]/15 shrink-0 glow-pulse">
            <svg className="w-[22px] h-[22px] sm:w-6 sm:h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <h1 className="font-display text-xl sm:text-[1.65rem] font-extrabold tracking-tight text-slate-900 leading-none">
            Academic
            <span className="bg-gradient-to-r from-[#2d6a4f] to-[#40916c] bg-clip-text text-transparent">Paraphraser</span>
          </h1>
        </div>
        <div />
      </header>
    </div>
  );
}
