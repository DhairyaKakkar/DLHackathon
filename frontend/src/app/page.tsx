import Link from "next/link";
import { BrainCircuit, Clock, Shuffle, Target, ArrowRight, GraduationCap } from "lucide-react";

const PILLARS = [
  {
    icon: Clock,
    title: "Retention",
    glowColor: "#3b82f6",
    desc: "Does knowledge survive a time gap? We retest at +1d, +3d, and +7d to compute a forgetting curve.",
  },
  {
    icon: Shuffle,
    title: "Transfer",
    glowColor: "#8b5cf6",
    desc: "Does knowledge generalise? We test variants with different wording, numbers, and context.",
  },
  {
    icon: Target,
    title: "Calibration",
    glowColor: "#f43f5e",
    desc: "Is confidence accurate? We compare self-reported confidence against actual accuracy bin by bin.",
  },
];

const DEMOS = [
  {
    id: 1,
    href: "/student/1",
    name: "Alice Chen",
    tag: "Fragile Mastery",
    tagColor: "#f43f5e",
    desc: "High mastery on originals — fails every variant. Knows the answers, not the concept.",
    dus: 47,
    dugColor: "#f43f5e",
  },
  {
    id: 2,
    href: "/student/2",
    name: "Bob Martinez",
    tag: "Overconfident",
    tagColor: "#f59e0b",
    desc: "Confidence 9/10, accuracy near 0. Severely miscalibrated — a calibration disaster.",
    dus: 18,
    dugColor: "#f59e0b",
  },
  {
    id: 3,
    href: "/faculty",
    name: "Faculty View",
    tag: "Cohort Analytics",
    tagColor: "#6366f1",
    desc: "Cohort-level insights: low-retention topics, transfer failures, overconfidence hotspots.",
    dus: null,
    dugColor: "#6366f1",
    isFaculty: true,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#09090f] overflow-x-hidden">
      {/* Ambient background blobs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[10%] w-[600px] h-[600px] bg-indigo-600/8 rounded-full blur-[120px]" />
        <div className="absolute top-[30%] right-[-10%] w-[400px] h-[400px] bg-violet-600/6 rounded-full blur-[100px]" />
        <div className="absolute bottom-[10%] left-[20%] w-[300px] h-[300px] bg-blue-600/5 rounded-full blur-[80px]" />
      </div>

      {/* Navbar */}
      <nav className="bg-[#09090f]/80 backdrop-blur-xl border-b border-white/[0.06] sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <BrainCircuit className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-sm text-white">EALE</span>
            <span className="hidden sm:block text-xs text-slate-600 ml-1">
              Evidence-Aligned Learning Engine
            </span>
          </div>
          <Link
            href="/login"
            className="flex items-center gap-1.5 bg-indigo-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Sign In
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </nav>

      <main className="relative max-w-5xl mx-auto px-4 sm:px-6 py-14">
        {/* Hero */}
        <section className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
            <BrainCircuit className="w-3.5 h-3.5" />
            Durable Learning Measurement
          </div>

          <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-white tracking-tight mb-4 leading-tight">
            Did they{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
              really
            </span>{" "}
            learn it?
          </h1>

          <p className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Raw scores only tell you if a student got it right{" "}
            <em className="text-slate-300">today</em>. EALE measures whether knowledge is{" "}
            <strong className="text-slate-200 font-semibold">retained over time</strong>,{" "}
            <strong className="text-slate-200 font-semibold">transferable to new contexts</strong>, and backed by{" "}
            <strong className="text-slate-200 font-semibold">calibrated confidence</strong>.
          </p>

          {/* DUS Formula pill */}
          <div className="mt-6 inline-block bg-white/[0.05] border border-white/[0.08] text-slate-400 text-xs font-mono px-5 py-2.5 rounded-xl">
            DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration
          </div>
        </section>

        {/* Demo cards */}
        <section className="mb-16">
          <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-widest text-center mb-6">
            Live Demo — Click to explore
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {DEMOS.map((demo) => (
              <Link
                key={demo.id}
                href={demo.href}
                className="group relative bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 hover:border-white/[0.18] transition-all hover:-translate-y-0.5 cursor-pointer overflow-hidden"
                style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.4)" }}
              >
                {/* Hover glow */}
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl pointer-events-none"
                  style={{
                    background: `radial-gradient(circle at 50% 0%, ${demo.dugColor}12, transparent 70%)`,
                  }}
                />

                <div className="relative">
                  {/* Tag */}
                  <span
                    className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full border mb-4"
                    style={{
                      color: demo.tagColor,
                      borderColor: `${demo.tagColor}40`,
                      background: `${demo.tagColor}12`,
                    }}
                  >
                    {demo.tag}
                  </span>

                  {/* Name + DUS */}
                  <div className="flex items-end justify-between mb-3">
                    <h3 className="text-lg font-bold text-white">
                      {demo.name}
                    </h3>
                    {demo.dus !== null && (
                      <div className="flex flex-col items-end">
                        <span
                          className="text-3xl font-black tabular-nums leading-none"
                          style={{ color: demo.dugColor }}
                        >
                          {demo.dus}
                        </span>
                        <span className="text-xs text-slate-600">DUS</span>
                      </div>
                    )}
                    {demo.isFaculty && (
                      <GraduationCap
                        className="w-8 h-8"
                        style={{ color: demo.dugColor }}
                      />
                    )}
                  </div>

                  <p className="text-sm text-slate-400 leading-relaxed mb-4">
                    {demo.desc}
                  </p>

                  <div className="flex items-center gap-1 text-sm font-semibold text-slate-500 group-hover:text-indigo-400 transition-colors">
                    View dashboard
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Pillars */}
        <section className="mb-12">
          <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-widest text-center mb-6">
            Three evidence pillars
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PILLARS.map(({ icon: Icon, title, glowColor, desc }) => (
              <div
                key={title}
                className="bg-white/[0.04] border border-white/[0.08] rounded-xl p-5 hover:border-white/[0.15] transition-colors"
              >
                <div className="flex items-center gap-2 mb-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{
                      background: `${glowColor}15`,
                      border: `1px solid ${glowColor}30`,
                    }}
                  >
                    <Icon className="w-4 h-4" style={{ color: glowColor }} />
                  </div>
                  <span className="font-semibold text-slate-200">{title}</span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Footer note */}
        <p className="text-center text-xs text-slate-700">
          EALE · Hackathon MVP · Backend at{" "}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-600 hover:text-slate-400 underline transition-colors"
          >
            localhost:8000/docs
          </a>
        </p>
      </main>
    </div>
  );
}
