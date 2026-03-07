"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Zap, BookOpen, X, Loader2, ChevronRight, CheckCircle2,
  Clock, Target, Brain, Lightbulb, RotateCcw, Upload
} from "lucide-react";
import { getPreClassBrief, completePreClassBrief } from "@/lib/api";
import type { ClassScheduleOut, PreClassBrief, PrepQuestion } from "@/lib/types";
import { cn } from "@/lib/utils";
import ContentLessonModal from "./ContentLessonModal";

// ─── Readiness ring ───────────────────────────────────────────────────────────

function ReadinessRing({ score }: { score: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <svg width="72" height="72" viewBox="0 0 72 72">
      <circle cx="36" cy="36" r={r} fill="none" stroke="#f3f4f6" strokeWidth="6" />
      <circle
        cx="36" cy="36" r={r} fill="none"
        stroke={color} strokeWidth="6"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
        style={{ transition: "stroke-dasharray 0.8s ease" }}
      />
      <text x="36" y="40" textAnchor="middle" fontSize="14" fontWeight="700" fill={color}>
        {Math.round(score)}
      </text>
    </svg>
  );
}

// ─── Quiz sub-component ───────────────────────────────────────────────────────

function PrepQuiz({
  questions,
  onComplete,
}: {
  questions: PrepQuestion[];
  onComplete: () => void;
}) {
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [textAnswer, setTextAnswer] = useState("");
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);

  const q = questions[idx];
  const isCorrect = selected === q?.correct || textAnswer.trim().toLowerCase() === q?.correct.toLowerCase();

  function handleReveal() {
    if (q.type === "MCQ" && !selected) return;
    if (q.type === "SHORT_TEXT" && !textAnswer.trim()) return;
    setRevealed(true);
    if (isCorrect) setScore(s => s + 1);
  }

  function handleNext() {
    if (idx < questions.length - 1) {
      setIdx(i => i + 1);
      setSelected(null);
      setTextAnswer("");
      setRevealed(false);
    } else {
      setFinished(true);
    }
  }

  if (finished) {
    const pct = Math.round((score / questions.length) * 100);
    return (
      <div className="flex flex-col items-center gap-4 py-6 text-center">
        <ReadinessRing score={pct} />
        <div>
          <p className="text-lg font-bold text-gray-900">{score}/{questions.length} correct</p>
          <p className="text-sm text-gray-500 mt-1">
            {pct >= 80 ? "Excellent prep! You're ready for class." : pct >= 50 ? "Good start — review the focus areas again." : "Keep studying — focus on the review points above."}
          </p>
        </div>
        <button onClick={onComplete} className="bg-[#111113] text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-[#2a2a32] transition-colors">
          Done — mark brief complete
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 font-medium">Question {idx + 1} of {questions.length}</span>
        <div className="flex gap-1">
          {questions.map((_, i) => (
            <div key={i} className={cn("w-2 h-2 rounded-full", i < idx ? "bg-emerald-400" : i === idx ? "bg-[#e8325a]" : "bg-gray-200")} />
          ))}
        </div>
      </div>

      <p className="text-sm font-semibold text-gray-900 leading-snug">{q.question}</p>

      {q.type === "MCQ" && q.options ? (
        <div className="flex flex-col gap-2">
          {q.options.map(opt => (
            <button
              key={opt}
              disabled={revealed}
              onClick={() => setSelected(opt)}
              className={cn(
                "text-left px-4 py-2.5 rounded-xl border text-sm transition-all",
                revealed
                  ? opt === q.correct
                    ? "bg-emerald-50 border-emerald-400 text-emerald-700 font-semibold"
                    : opt === selected && opt !== q.correct
                      ? "bg-red-50 border-red-300 text-red-600"
                      : "bg-gray-50 border-gray-200 text-gray-400"
                  : selected === opt
                    ? "bg-[#111113] border-[#111113] text-white"
                    : "bg-white border-gray-200 hover:border-gray-400 text-gray-700"
              )}
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        <textarea
          value={textAnswer}
          onChange={e => setTextAnswer(e.target.value)}
          disabled={revealed}
          placeholder="Type your answer…"
          rows={3}
          className="border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a] resize-none"
        />
      )}

      {revealed && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
          <p className="text-xs font-semibold text-blue-700 mb-1">Explanation</p>
          <p className="text-xs text-blue-600">{q.explanation}</p>
        </div>
      )}

      <button
        onClick={revealed ? handleNext : handleReveal}
        disabled={!revealed && !selected && !textAnswer.trim()}
        className="bg-[#111113] text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-[#2a2a32] disabled:opacity-40 transition-colors"
      >
        {revealed ? (idx < questions.length - 1 ? "Next question →" : "See results →") : "Check answer"}
      </button>
    </div>
  );
}

// ─── Brief panel ─────────────────────────────────────────────────────────────

function BriefPanel({
  scheduleId,
  studentId,
  subject,
  hoursUntil,
  onClose,
}: {
  scheduleId: number;
  studentId: number;
  subject: string;
  hoursUntil: number;
  onClose: () => void;
}) {
  const [view, setView] = useState<"brief" | "quiz">("brief");
  const qc = useQueryClient();

  const { data: brief, isLoading, isError } = useQuery<PreClassBrief>({
    queryKey: ["preClassBrief", studentId, scheduleId],
    queryFn: () => getPreClassBrief(studentId, scheduleId),
    staleTime: 1000 * 60 * 60, // 1h cache
  });

  const completeMutation = useMutation({
    mutationFn: () => completePreClassBrief(studentId, scheduleId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedule", studentId] });
      onClose();
    },
  });

  const hoursLabel = hoursUntil < 1 ? "< 1 hour" : hoursUntil < 24 ? `${Math.round(hoursUntil)}h` : `${Math.round(hoursUntil / 24)}d`;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 pt-5 pb-4 flex items-start justify-between gap-3 rounded-t-2xl">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Pre-class prep</span>
            </div>
            <h2 className="text-base font-bold text-gray-900">{subject}</h2>
            <p className="text-xs text-gray-400">Class in {hoursLabel}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors mt-0.5">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-5 py-5">
          {isLoading && (
            <div className="flex flex-col items-center gap-4 py-12">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              <div className="text-center">
                <p className="text-sm font-semibold text-gray-700">GPT-4o is analysing your performance…</p>
                <p className="text-xs text-gray-400 mt-1">Building your personalised prep brief</p>
              </div>
            </div>
          )}

          {isError && (
            <div className="text-center py-8">
              <p className="text-sm text-red-500">Failed to generate brief. Check your API key.</p>
            </div>
          )}

          {brief && view === "brief" && (
            <div className="flex flex-col gap-5">
              {/* Readiness + summary */}
              <div className="flex items-start gap-4 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-100">
                <ReadinessRing score={brief.readiness_score} />
                <div className="flex-1">
                  <p className="text-xs font-semibold text-indigo-700 mb-1">Readiness score</p>
                  <p className="text-sm text-gray-700 leading-snug">{brief.summary}</p>
                </div>
              </div>

              {/* Focus areas */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-[#e8325a]" />
                  <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Focus areas</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {brief.focus_areas.map(f => (
                    <span key={f} className="text-xs bg-red-50 text-red-700 border border-red-200 px-3 py-1 rounded-full font-medium">{f}</span>
                  ))}
                </div>
              </div>

              {/* Quick review */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-indigo-500" />
                  <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Quick review</span>
                </div>
                <div className="flex flex-col gap-2">
                  {brief.quick_review_points.map((pt, i) => (
                    <div key={i} className="flex items-start gap-2.5 bg-gray-50 rounded-xl px-3 py-2.5">
                      <span className="text-xs font-bold text-indigo-400 mt-0.5 shrink-0">{i + 1}</span>
                      <p className="text-sm text-gray-700">{pt}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Personalized tip */}
              <div className="flex items-start gap-3 bg-amber-50 border border-amber-100 rounded-xl p-3">
                <Lightbulb className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-700">{brief.personalized_tip}</p>
              </div>

              {/* Estimated time + CTA */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                  <Clock className="w-3.5 h-3.5" />
                  {brief.estimated_prep_time}
                </div>
                <button
                  onClick={() => setView("quiz")}
                  className="flex-1 flex items-center justify-center gap-2 bg-[#111113] text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-[#2a2a32] transition-colors"
                >
                  <BookOpen className="w-4 h-4" />
                  Start prep quiz ({brief.prep_questions.length} questions)
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {brief && view === "quiz" && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <button onClick={() => setView("brief")} className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600">
                  <RotateCcw className="w-3.5 h-3.5" /> Back to brief
                </button>
                <span className="text-xs text-gray-400">{subject} prep quiz</span>
              </div>
              <PrepQuiz
                questions={brief.prep_questions}
                onComplete={() => completeMutation.mutate()}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main alert banner ────────────────────────────────────────────────────────

export default function PreClassAlert({
  urgentClasses,
  studentId,
}: {
  urgentClasses: ClassScheduleOut[];
  studentId: number;
}) {
  const [openBriefId, setOpenBriefId] = useState<number | null>(null);
  const [openContentId, setOpenContentId] = useState<number | null>(null);
  const [dismissed, setDismissed] = useState(false);

  if (!urgentClasses.length || dismissed) return null;

  const primary = urgentClasses[0];
  const openSchedule = urgentClasses.find(c => c.id === openBriefId);
  const openContentSchedule = urgentClasses.find(c => c.id === openContentId);
  const showContentUpload =
    primary.days_until_next_class !== null && primary.days_until_next_class <= 2;

  return (
    <>
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center shrink-0">
          <Zap className="w-5 h-5 text-amber-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-amber-800">
              ⚡ {primary.is_urgent ? "Class today:" : "Coming up:"} {primary.subject_name}
            </span>
            {primary.hours_until_next_class !== null && (
              <span className="text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full font-medium">
                in {primary.hours_until_next_class < 1 ? "< 1h" : primary.hours_until_next_class < 24 ? `${Math.round(primary.hours_until_next_class)}h` : `${primary.days_until_next_class}d`}
              </span>
            )}
            {primary.readiness_score !== null && (
              <span className={cn(
                "text-xs px-2 py-0.5 rounded-full font-medium",
                primary.readiness_score >= 75 ? "bg-emerald-100 text-emerald-700" : primary.readiness_score >= 50 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
              )}>
                {Math.round(primary.readiness_score)}% ready
              </span>
            )}
          </div>
          <p className="text-xs text-amber-600 mt-0.5">
            {primary.readiness_score !== null && primary.readiness_score < 70
              ? "Your readiness score suggests you should review before class."
              : "Get a personalised prep brief to walk in confident."}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {showContentUpload && (
            <button
              onClick={() => setOpenContentId(primary.id)}
              className="flex items-center gap-1.5 bg-indigo-600 text-white px-3 py-2 rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload content
            </button>
          )}
          <button
            onClick={() => setOpenBriefId(primary.id)}
            className="flex items-center gap-1.5 bg-amber-600 text-white px-3 py-2 rounded-lg text-xs font-semibold hover:bg-amber-700 transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5" />
            Start prep
          </button>
          <button onClick={() => setDismissed(true)} className="text-amber-400 hover:text-amber-600 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {openSchedule && openBriefId !== null && (
        <BriefPanel
          scheduleId={openBriefId}
          studentId={studentId}
          subject={openSchedule.subject_name}
          hoursUntil={openSchedule.hours_until_next_class ?? 24}
          onClose={() => setOpenBriefId(null)}
        />
      )}

      {openContentSchedule && openContentId !== null && (
        <ContentLessonModal
          studentId={studentId}
          scheduleId={openContentId}
          subjectName={openContentSchedule.subject_name}
          onClose={() => setOpenContentId(null)}
        />
      )}
    </>
  );
}
