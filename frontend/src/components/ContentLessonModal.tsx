"use client";

import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  X, Upload, FileText, Image, Loader2, BookOpen,
  ChevronRight, CheckCircle2, AlertCircle, Lightbulb,
  Brain, Clock, RotateCcw, Star
} from "lucide-react";
import { uploadClassContent, getClassLesson, getPreLectureQuiz } from "@/lib/api";
import type { ContentLesson, PreLectureQuiz, PreLectureQuizQuestion } from "@/lib/types";
import { cn } from "@/lib/utils";

// ─── Step types ───────────────────────────────────────────────────────────────

type Step = "upload" | "lesson" | "quiz" | "done";

// ─── Pre-lecture quiz sub-component ──────────────────────────────────────────

function PreLectureQuizView({
  quiz,
  onDone,
}: {
  quiz: PreLectureQuiz;
  onDone: (score: number, total: number) => void;
}) {
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [textAnswer, setTextAnswer] = useState("");
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState(0);

  const q: PreLectureQuizQuestion = quiz.questions[idx];
  const isCorrect =
    selected === q?.correct ||
    textAnswer.trim().toLowerCase() === q?.correct.toLowerCase();

  function handleReveal() {
    if (q.type === "MCQ" && !selected) return;
    if (q.type === "SHORT_TEXT" && !textAnswer.trim()) return;
    setRevealed(true);
    if (isCorrect) setScore(s => s + 1);
  }

  function handleNext() {
    if (idx < quiz.questions.length - 1) {
      setIdx(i => i + 1);
      setSelected(null);
      setTextAnswer("");
      setRevealed(false);
    } else {
      onDone(isCorrect ? score + 1 : score, quiz.questions.length);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-400 font-medium">
          Question {idx + 1} of {quiz.questions.length}
        </span>
        <div className="flex gap-1">
          {quiz.questions.map((_, i) => (
            <div
              key={i}
              className={cn(
                "w-2 h-2 rounded-full",
                i < idx ? "bg-emerald-400" : i === idx ? "bg-indigo-500" : "bg-gray-200"
              )}
            />
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
                    ? "bg-indigo-600 border-indigo-600 text-white"
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
          placeholder="Type your answer..."
          rows={3}
          className="border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 resize-none"
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
        className="bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-colors"
      >
        {revealed
          ? idx < quiz.questions.length - 1 ? "Next question →" : "See results →"
          : "Check answer"}
      </button>
    </div>
  );
}

// ─── Main modal ───────────────────────────────────────────────────────────────

export default function ContentLessonModal({
  studentId,
  scheduleId,
  subjectName,
  onClose,
}: {
  studentId: number;
  scheduleId: number;
  subjectName: string;
  onClose: () => void;
}) {
  const [step, setStep] = useState<Step>("upload");
  const [uploadMode, setUploadMode] = useState<"text" | "image">("text");
  const [textContent, setTextContent] = useState("");
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [imageType, setImageType] = useState<string>("image/jpeg");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [lesson, setLesson] = useState<ContentLesson | null>(null);
  const [quiz, setQuiz] = useState<PreLectureQuiz | null>(null);
  const [quizScore, setQuizScore] = useState<{ score: number; total: number } | null>(null);
  const [expandedConcept, setExpandedConcept] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 1: upload content
  const uploadMutation = useMutation({
    mutationFn: () =>
      uploadClassContent(studentId, scheduleId, {
        text: uploadMode === "text" ? textContent : undefined,
        image_b64: uploadMode === "image" ? (imageB64 ?? undefined) : undefined,
        media_type: uploadMode === "image" ? imageType : undefined,
      }),
    onSuccess: async () => {
      // Fetch lesson immediately after upload
      const lessonData = await getClassLesson(studentId, scheduleId);
      setLesson(lessonData);
      setStep("lesson");
    },
  });

  // Step 3: load quiz
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState(false);

  async function handleStartQuiz() {
    setQuizLoading(true);
    setQuizError(false);
    try {
      const quizData = await getPreLectureQuiz(studentId, scheduleId);
      setQuiz(quizData);
      setStep("quiz");
    } catch {
      setQuizError(true);
    } finally {
      setQuizLoading(false);
    }
  }

  function handleImageSelect(file: File) {
    setImageType(file.type || "image/jpeg");
    setImagePreview(URL.createObjectURL(file));
    const reader = new FileReader();
    reader.onload = e => {
      const dataUrl = e.target?.result as string;
      setImageB64(dataUrl.split(",")[1]);
    };
    reader.readAsDataURL(file);
  }

  const canUpload =
    uploadMode === "text" ? textContent.trim().length >= 20 : imageB64 !== null;

  // ─── Render upload step ──────────────────────────────────────────────────

  function renderUpload() {
    return (
      <div className="flex flex-col gap-5">
        <div>
          <p className="text-sm text-gray-600 mb-4">
            Share what will be covered in your upcoming <strong>{subjectName}</strong> class.
            AI will teach you the key concepts and prepare a diagnostic quiz.
          </p>

          {/* Mode toggle */}
          <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-4">
            <button
              onClick={() => setUploadMode("text")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-all",
                uploadMode === "text"
                  ? "bg-white shadow-sm text-gray-900"
                  : "text-gray-500 hover:text-gray-700"
              )}
            >
              <FileText className="w-3.5 h-3.5" /> Paste text
            </button>
            <button
              onClick={() => setUploadMode("image")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-all",
                uploadMode === "image"
                  ? "bg-white shadow-sm text-gray-900"
                  : "text-gray-500 hover:text-gray-700"
              )}
            >
              <Image className="w-3.5 h-3.5" /> Upload slide/photo
            </button>
          </div>

          {uploadMode === "text" ? (
            <textarea
              value={textContent}
              onChange={e => setTextContent(e.target.value)}
              placeholder="Paste lecture notes, syllabus topics, or a description of what will be covered..."
              rows={7}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 resize-none"
            />
          ) : (
            <div className="flex flex-col gap-3">
              {imagePreview ? (
                <div className="relative">
                  <img
                    src={imagePreview}
                    alt="Uploaded content"
                    className="w-full max-h-52 object-contain rounded-xl border border-gray-200 bg-gray-50"
                  />
                  <button
                    onClick={() => { setImagePreview(null); setImageB64(null); }}
                    className="absolute top-2 right-2 w-6 h-6 bg-white rounded-full shadow flex items-center justify-center text-gray-500 hover:text-gray-800"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-200 rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer hover:border-indigo-300 hover:bg-indigo-50/30 transition-all"
                >
                  <Upload className="w-8 h-8 text-gray-300" />
                  <div className="text-center">
                    <p className="text-sm font-medium text-gray-600">Upload lecture slide or whiteboard photo</p>
                    <p className="text-xs text-gray-400 mt-1">PNG, JPG up to 10MB</p>
                  </div>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) handleImageSelect(f); }}
              />
            </div>
          )}
        </div>

        {uploadMutation.isError && (
          <div className="flex items-center gap-2 text-red-500 text-xs bg-red-50 border border-red-100 rounded-xl px-3 py-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            Failed to process content. Check your API key and try again.
          </div>
        )}

        <button
          onClick={() => uploadMutation.mutate()}
          disabled={!canUpload || uploadMutation.isPending}
          className="flex items-center justify-center gap-2 bg-indigo-600 text-white py-3 rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-colors"
        >
          {uploadMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              GPT-4o is processing your content...
            </>
          ) : (
            <>
              <Brain className="w-4 h-4" />
              Teach me this content
              <ChevronRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    );
  }

  // ─── Render lesson step ──────────────────────────────────────────────────

  function renderLesson() {
    if (!lesson) return null;
    return (
      <div className="flex flex-col gap-5">
        {/* Overview */}
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen className="w-4 h-4 text-indigo-600" />
            <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wider">Overview</span>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{lesson.overview}</p>
          <div className="flex items-center gap-1.5 mt-3 text-xs text-indigo-500">
            <Clock className="w-3.5 h-3.5" />
            {lesson.estimated_time}
          </div>
        </div>

        {/* Key concepts */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-[#e8325a]" />
            <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Key Concepts</span>
          </div>
          <div className="flex flex-col gap-2">
            {lesson.key_concepts.map((concept, i) => (
              <div
                key={i}
                className="border border-gray-100 rounded-xl overflow-hidden"
              >
                <button
                  onClick={() => setExpandedConcept(expandedConcept === i ? null : i)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm font-semibold text-gray-900">{concept.name}</span>
                  <ChevronRight
                    className={cn(
                      "w-4 h-4 text-gray-400 transition-transform",
                      expandedConcept === i && "rotate-90"
                    )}
                  />
                </button>
                {expandedConcept === i && (
                  <div className="px-4 pb-4 flex flex-col gap-3 bg-gray-50/50">
                    <p className="text-sm text-gray-700">{concept.explanation}</p>
                    <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                      <p className="text-xs font-semibold text-emerald-700 mb-1">Example</p>
                      <p className="text-xs text-emerald-600">{concept.example}</p>
                    </div>
                    <div className="bg-red-50 border border-red-100 rounded-lg p-3">
                      <p className="text-xs font-semibold text-red-600 mb-1">Common mistake</p>
                      <p className="text-xs text-red-500">{concept.common_mistake}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Quick facts */}
        {lesson.quick_facts.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Star className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Quick Facts</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {lesson.quick_facts.map((fact, i) => (
                <div key={i} className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                  <span className="text-amber-400 font-bold text-xs mt-0.5 shrink-0">•</span>
                  <p className="text-xs text-amber-800">{fact}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Lecture tip */}
        <div className="flex items-start gap-3 bg-blue-50 border border-blue-100 rounded-xl p-3">
          <Lightbulb className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-blue-700 mb-1">Lecture tip</p>
            <p className="text-xs text-blue-600">{lesson.lecture_tip}</p>
          </div>
        </div>

        {/* CTA */}
        <div className="flex gap-3">
          {quizError && (
            <p className="text-xs text-red-500 flex-1">Failed to generate quiz. Try again.</p>
          )}
          <button
            onClick={handleStartQuiz}
            disabled={quizLoading}
            className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 text-white py-3 rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-colors"
          >
            {quizLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating quiz...
              </>
            ) : (
              <>
                Take pre-assessment
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // ─── Render quiz step ────────────────────────────────────────────────────

  function renderQuiz() {
    if (!quiz) return null;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setStep("lesson")}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Back to lesson
          </button>
          <span className="text-xs text-gray-400">
            Pass: {quiz.passing_score}%
          </span>
        </div>

        {quiz.diagnostic_note && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl px-3 py-2">
            <p className="text-xs text-blue-600">{quiz.diagnostic_note}</p>
          </div>
        )}

        <PreLectureQuizView
          quiz={quiz}
          onDone={(score, total) => {
            setQuizScore({ score, total });
            setStep("done");
          }}
        />
      </div>
    );
  }

  // ─── Render done step ────────────────────────────────────────────────────

  function renderDone() {
    if (!quizScore) return null;
    const pct = Math.round((quizScore.score / quizScore.total) * 100);
    const passed = pct >= (quiz?.passing_score ?? 70);
    return (
      <div className="flex flex-col items-center gap-5 py-6 text-center">
        <div
          className={cn(
            "w-16 h-16 rounded-2xl flex items-center justify-center",
            passed ? "bg-emerald-100" : "bg-amber-100"
          )}
        >
          {passed
            ? <CheckCircle2 className="w-8 h-8 text-emerald-600" />
            : <Brain className="w-8 h-8 text-amber-600" />}
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{pct}%</p>
          <p className="text-base font-semibold text-gray-700 mt-1">
            {quizScore.score} / {quizScore.total} correct
          </p>
          <p className="text-sm text-gray-500 mt-2 max-w-xs">
            {passed
              ? "Great job! You're well-prepared for this lecture."
              : "Review the lesson concepts before class to strengthen your understanding."}
          </p>
        </div>
        <div className="flex gap-3 w-full">
          {!passed && (
            <button
              onClick={() => { setStep("lesson"); setExpandedConcept(null); }}
              className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Review lesson
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    );
  }

  // ─── Step labels ─────────────────────────────────────────────────────────

  const stepLabels: Record<Step, string> = {
    upload: "Upload content",
    lesson: "AI lesson",
    quiz: "Pre-assessment",
    done: "Results",
  };

  const stepOrder: Step[] = ["upload", "lesson", "quiz", "done"];

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 pt-5 pb-4 flex items-start justify-between gap-3 rounded-t-2xl">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="w-4 h-4 text-indigo-500" />
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">
                Pre-lecture prep
              </span>
            </div>
            <h2 className="text-base font-bold text-gray-900">{subjectName}</h2>
            <p className="text-xs text-gray-400">{stepLabels[step]}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors mt-0.5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step progress */}
        <div className="flex items-center gap-1 px-5 py-3 border-b border-gray-50">
          {stepOrder.map((s, i) => {
            const currentIdx = stepOrder.indexOf(step);
            const isDone = i < currentIdx;
            const isCurrent = s === step;
            return (
              <div key={s} className="flex items-center gap-1 flex-1">
                <div
                  className={cn(
                    "w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
                    isDone ? "bg-emerald-500 text-white" :
                    isCurrent ? "bg-indigo-600 text-white" :
                    "bg-gray-100 text-gray-400"
                  )}
                >
                  {isDone ? <CheckCircle2 className="w-3 h-3" /> : i + 1}
                </div>
                {i < stepOrder.length - 1 && (
                  <div className={cn("flex-1 h-0.5 rounded", isDone ? "bg-emerald-300" : "bg-gray-100")} />
                )}
              </div>
            );
          })}
        </div>

        <div className="px-5 py-5">
          {step === "upload" && renderUpload()}
          {step === "lesson" && renderLesson()}
          {step === "quiz" && renderQuiz()}
          {step === "done" && renderDone()}
        </div>
      </div>
    </div>
  );
}
