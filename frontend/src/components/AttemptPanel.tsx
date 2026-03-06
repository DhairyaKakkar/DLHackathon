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
      queryClient.invalidateQueries({ queryKey: ["tasks", studentId] });
      queryClient.invalidateQueries({ queryKey: ["studentDashboard", studentId] });
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error("Submission failed", { description: err.message });
    },
  });

  const canSubmit = answer.trim().length > 0 && !mutation.isPending && !submitted;

  const confidenceLabels: Record<number, string> = {
    1: "Guessing", 2: "Unsure", 3: "Uncertain", 4: "Low",
    5: "Moderate", 6: "Fairly sure", 7: "Confident",
    8: "Very confident", 9: "Almost certain", 10: "Certain",
  };

  if (submitted) {
    return (
      <div
        className={cn(
          "flex flex-col gap-3 p-4 rounded-xl border animate-fade-in",
          submitted.isCorrect
            ? "bg-emerald-50 border-emerald-200"
            : "bg-red-50 border-red-200",
        )}
      >
        <div className="flex items-center gap-2">
          {submitted.isCorrect ? (
            <CheckCircle className="w-5 h-5 text-emerald-600" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
          <span className={cn("font-semibold", submitted.isCorrect ? "text-emerald-700" : "text-red-600")}>
            {submitted.isCorrect ? "Correct!" : "Incorrect"}
          </span>
        </div>
        {!submitted.isCorrect && (
          <p className="text-sm text-red-600">
            Correct answer: <span className="font-semibold">{question.correct_answer}</span>
          </p>
        )}
        <p className="text-xs text-[#9e9eae]">
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
                  ? "bg-[#fff0f3] border-[#e8325a] ring-1 ring-[#e8325a]/30"
                  : "bg-white border-[#d0cec9] hover:border-[#111113] hover:bg-[#fafaf8]",
              )}
            >
              <input
                type="radio"
                name={`q-${question.id}`}
                value={opt}
                checked={answer === opt}
                onChange={() => setAnswer(opt)}
                className="accent-[#e8325a]"
              />
              <span className="text-sm text-[#111113]">{opt}</span>
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
          className="w-full px-3 py-2 text-sm bg-white border border-[#d0cec9] rounded-lg text-[#111113] placeholder-[#9e9eae] focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a] transition-colors"
        />
      )}

      {/* Confidence slider */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-[#5c5c6e]">
            Confidence: {confidence}/10
          </span>
          <span className="text-xs text-[#9e9eae] italic">
            {confidenceLabels[confidence]}
          </span>
        </div>
        <input
          type="range"
          min={1} max={10} step={1}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="w-full cursor-pointer"
        />
        <div className="flex justify-between text-xs text-[#9e9eae]">
          <span>Guessing</span>
          <span>Certain</span>
        </div>
      </div>

      {/* Optional reasoning */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-[#5c5c6e]">
          Reasoning <span className="font-normal text-[#9e9eae]">(optional)</span>
        </label>
        <textarea
          rows={2}
          placeholder="Explain your thinking…"
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          className="w-full px-3 py-2 text-sm bg-white border border-[#d0cec9] rounded-lg text-[#111113] placeholder-[#9e9eae] focus:outline-none focus:ring-2 focus:ring-[#e8325a]/20 focus:border-[#e8325a] resize-none transition-colors"
        />
      </div>

      {/* Submit */}
      <button
        onClick={() => mutation.mutate()}
        disabled={!canSubmit}
        className={cn(
          "flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all",
          canSubmit
            ? "bg-[#111113] text-white hover:bg-[#2a2a32] active:scale-95"
            : "bg-black/[0.06] text-[#9e9eae] cursor-not-allowed",
        )}
      >
        {mutation.isPending ? (
          <><Loader2 className="w-4 h-4 animate-spin" />Submitting…</>
        ) : (
          <><Send className="w-4 h-4" />Submit Answer</>
        )}
      </button>
    </div>
  );
}
