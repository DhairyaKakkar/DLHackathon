"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Send, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { submitAttempt } from "@/lib/api";
import type { Question } from "@/lib/types";

interface AttemptPanelProps {
  question: Question;
  studentId: number;
  onSuccess?: () => void;
}

export default function AttemptPanel({
  question,
  studentId,
  onSuccess,
}: AttemptPanelProps) {
  const [answer, setAnswer] = useState("");
  const [confidence, setConfidence] = useState(5);
  const [reasoning, setReasoning] = useState("");
  const [submitted, setSubmitted] = useState<{
    isCorrect: boolean;
    answer: string;
  } | null>(null);

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      submitAttempt({
        student_id: studentId,
        question_id: question.id,
        answer: answer.trim(),
        confidence,
        reasoning: reasoning.trim() || undefined,
      }),
    onSuccess: (result) => {
      if (result.is_correct) {
        toast.success("Correct! Well done.", {
          description: `Confidence was ${confidence}/10`,
          icon: "✅",
        });
      } else {
        toast.error("Incorrect.", {
          description: `Correct answer: "${question.correct_answer}"`,
          icon: "❌",
        });
      }
      setSubmitted({ isCorrect: result.is_correct, answer: result.answer });
      // Invalidate tasks and dashboard so they refresh
      queryClient.invalidateQueries({
        queryKey: ["tasks", studentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["studentDashboard", studentId],
      });
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error("Submission failed", { description: err.message });
    },
  });

  const canSubmit =
    answer.trim().length > 0 && !mutation.isPending && !submitted;

  const confidenceLabels: Record<number, string> = {
    1: "Guessing",
    2: "Unsure",
    3: "Uncertain",
    4: "Low",
    5: "Moderate",
    6: "Fairly sure",
    7: "Confident",
    8: "Very confident",
    9: "Almost certain",
    10: "Certain",
  };

  if (submitted) {
    return (
      <div
        className={cn(
          "flex flex-col gap-3 p-4 rounded-xl border animate-fade-in",
          submitted.isCorrect
            ? "bg-green-50 border-green-200"
            : "bg-red-50 border-red-200",
        )}
      >
        <div className="flex items-center gap-2">
          {submitted.isCorrect ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
          <span
            className={cn(
              "font-semibold",
              submitted.isCorrect ? "text-green-700" : "text-red-700",
            )}
          >
            {submitted.isCorrect ? "Correct!" : "Incorrect"}
          </span>
        </div>
        {!submitted.isCorrect && (
          <p className="text-sm text-red-600">
            Correct answer:{" "}
            <span className="font-semibold">{question.correct_answer}</span>
          </p>
        )}
        <p className="text-xs text-gray-500">
          Your confidence was {confidence}/10. Task marked complete.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 animate-fade-in">
      {/* MCQ options */}
      {question.question_type === "MCQ" && question.options && (
        <div className="flex flex-col gap-2">
          {question.options.map((opt) => (
            <label
              key={opt}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all",
                answer === opt
                  ? "bg-brand-50 border-brand-500 ring-1 ring-brand-500"
                  : "bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50",
              )}
            >
              <input
                type="radio"
                name={`q-${question.id}`}
                value={opt}
                checked={answer === opt}
                onChange={() => setAnswer(opt)}
                className="accent-indigo-600"
              />
              <span className="text-sm text-gray-700">{opt}</span>
            </label>
          ))}
        </div>
      )}

      {/* Short text input */}
      {question.question_type === "SHORT_TEXT" && (
        <input
          type="text"
          placeholder="Your answer…"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && canSubmit && mutation.mutate()}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
        />
      )}

      {/* Confidence slider */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-500">
            Confidence: {confidence}/10
          </span>
          <span className="text-xs text-gray-400 italic">
            {confidenceLabels[confidence]}
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={10}
          step={1}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="w-full accent-indigo-600 cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-300">
          <span>Guessing</span>
          <span>Certain</span>
        </div>
      </div>

      {/* Optional reasoning */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-500">
          Reasoning{" "}
          <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <textarea
          rows={2}
          placeholder="Explain your thinking…"
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 resize-none"
        />
      </div>

      {/* Submit */}
      <button
        onClick={() => mutation.mutate()}
        disabled={!canSubmit}
        className={cn(
          "flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all",
          canSubmit
            ? "bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95"
            : "bg-gray-100 text-gray-400 cursor-not-allowed",
        )}
      >
        {mutation.isPending ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Submitting…
          </>
        ) : (
          <>
            <Send className="w-4 h-4" />
            Submit Answer
          </>
        )}
      </button>
    </div>
  );
}
