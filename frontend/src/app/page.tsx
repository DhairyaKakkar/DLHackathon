import Link from "next/link";
import { BrainCircuit, Clock, Shuffle, Target, ArrowRight } from "lucide-react";

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

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      {/* Navbar */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-indigo-600" />
            <span className="font-bold text-sm text-gray-900">EALE</span>
            <span className="hidden sm:block text-xs text-gray-400 ml-1">
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

          {/* DUS formula pill */}
          <div className="mt-6 inline-block bg-gray-900 text-gray-100 text-xs font-mono px-5 py-2.5 rounded-xl shadow-sm">
            DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration
          </div>

          {/* CTA */}
          <div className="mt-10 flex justify-center">
            <Link
              href="/login"
              className="flex items-center gap-2 bg-indigo-600 text-white px-8 py-3.5 rounded-xl font-semibold text-base hover:bg-indigo-700 transition-all hover:scale-[1.02] active:scale-95 shadow-sm"
            >
              Sign In to Dashboard
              <ArrowRight className="w-5 h-5" />
            </Link>
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
