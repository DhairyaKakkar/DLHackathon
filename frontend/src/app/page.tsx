import Link from "next/link";
import { BrainCircuit, Clock, Shuffle, Target, ArrowRight, GraduationCap } from "lucide-react";

const PILLARS = [
  {
    icon: Clock,
    title: "Retention",
    color: "text-blue-500",
    bg: "bg-blue-50",
    border: "border-blue-100",
    desc: "Does knowledge survive a time gap? We retest at +1d, +3d, and +7d to compute a forgetting curve.",
  },
  {
    icon: Shuffle,
    title: "Transfer",
    color: "text-purple-500",
    bg: "bg-purple-50",
    border: "border-purple-100",
    desc: "Does knowledge generalise? We test variants with different wording, numbers, and context.",
  },
  {
    icon: Target,
    title: "Calibration",
    color: "text-rose-500",
    bg: "bg-rose-50",
    border: "border-rose-100",
    desc: "Is confidence accurate? We compare self-reported confidence against actual accuracy bin by bin.",
  },
];

const DEMOS = [
  {
    id: 1,
    href: "/student/1",
    name: "Alice Chen",
    tag: "Fragile Mastery",
    tagColor: "bg-red-100 text-red-700 border-red-200",
    desc: "High mastery on originals — fails every variant. Knows the answers, not the concept.",
    dus: 47,
    dusBg: "from-red-50 to-orange-50",
    dugColor: "#ef4444",
  },
  {
    id: 2,
    href: "/student/2",
    name: "Bob Martinez",
    tag: "Overconfident",
    tagColor: "bg-amber-100 text-amber-700 border-amber-200",
    desc: "Confidence 9/10, accuracy near 0. Severely miscalibrated — a calibration disaster.",
    dus: 18,
    dusBg: "from-amber-50 to-red-50",
    dugColor: "#f59e0b",
  },
  {
    id: 3,
    href: "/faculty",
    name: "Faculty View",
    tag: "Cohort Analytics",
    tagColor: "bg-indigo-100 text-indigo-700 border-indigo-200",
    desc: "Cohort-level insights: low-retention topics, transfer failures, overconfidence hotspots.",
    dus: null,
    dusBg: "from-indigo-50 to-blue-50",
    dugColor: "#4f46e5",
    isFaculty: true,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      {/* Navbar */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-2">
          <BrainCircuit className="w-5 h-5 text-indigo-600" />
          <span className="font-bold text-sm text-gray-900">EALE</span>
          <span className="hidden sm:block text-xs text-gray-400 ml-1">
            Evidence-Aligned Learning Engine
          </span>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-14">
        {/* Hero */}
        <section className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
            <BrainCircuit className="w-3.5 h-3.5" />
            Durable Learning Measurement
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 tracking-tight mb-4 leading-tight">
            Did they{" "}
            <span className="text-indigo-600">really</span>{" "}
            learn it?
          </h1>

          <p className="text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">
            Raw scores only tell you if a student got it right{" "}
            <em>today</em>. EALE measures whether knowledge is{" "}
            <strong className="text-gray-700">retained over time</strong>,{" "}
            <strong className="text-gray-700">transferable to new contexts</strong>, and backed by{" "}
            <strong className="text-gray-700">calibrated confidence</strong>.
          </p>

          {/* DUS Formula pill */}
          <div className="mt-6 inline-block bg-gray-900 text-gray-100 text-xs font-mono px-5 py-2.5 rounded-xl shadow-sm">
            DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration
          </div>
        </section>

        {/* Demo cards */}
        <section className="mb-16">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest text-center mb-6">
            Live Demo — Click to explore
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {DEMOS.map((demo) => (
              <Link
                key={demo.id}
                href={demo.href}
                className={`group relative bg-gradient-to-br ${demo.dusBg} border border-white/80 rounded-2xl p-6 shadow-card hover:shadow-card-hover transition-all hover:-translate-y-0.5 cursor-pointer overflow-hidden`}
              >
                {/* Background accent */}
                <div className="absolute inset-0 bg-white/40 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />

                <div className="relative">
                  {/* Tag */}
                  <span
                    className={`inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full border ${demo.tagColor} mb-4`}
                  >
                    {demo.tag}
                  </span>

                  {/* Name + DUS */}
                  <div className="flex items-end justify-between mb-3">
                    <h3 className="text-lg font-bold text-gray-900">
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
                        <span className="text-xs text-gray-400">DUS</span>
                      </div>
                    )}
                    {demo.isFaculty && (
                      <GraduationCap
                        className="w-8 h-8"
                        style={{ color: demo.dugColor }}
                      />
                    )}
                  </div>

                  <p className="text-sm text-gray-600 leading-relaxed mb-4">
                    {demo.desc}
                  </p>

                  <div className="flex items-center gap-1 text-sm font-semibold text-gray-700 group-hover:text-indigo-600 transition-colors">
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
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest text-center mb-6">
            Three evidence pillars
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PILLARS.map(({ icon: Icon, title, color, bg, border, desc }) => (
              <div
                key={title}
                className={`${bg} ${border} border rounded-xl p-5`}
              >
                <div className="flex items-center gap-2 mb-3">
                  <Icon className={`w-5 h-5 ${color}`} />
                  <span className="font-semibold text-gray-800">{title}</span>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Footer note */}
        <p className="text-center text-xs text-gray-300">
          EALE · Hackathon MVP · Backend at{" "}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-gray-400"
          >
            localhost:8000/docs
          </a>
        </p>
      </main>
    </div>
  );
}
