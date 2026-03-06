"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, RotateCcw, Shuffle } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import AttemptPanel from "./AttemptPanel";
import type { ScheduledTask } from "@/lib/types";

interface TaskCardProps {
  task: ScheduledTask;
  studentId: number;
  index: number;
}

export default function TaskCard({ task, studentId, index }: TaskCardProps) {
  const [expanded, setExpanded] = useState(index === 0);

  const isOverdue = new Date(task.due_at) < new Date();
  const isRetest = task.task_type === "RETEST";

  const typeStyles = isRetest
    ? "bg-blue-50 text-blue-700 border-blue-200"
    : "bg-violet-50 text-violet-700 border-violet-200";

  const TypeIcon = isRetest ? RotateCcw : Shuffle;

  return (
    <div
      className={cn(
        "bg-white rounded-xl border shadow-card overflow-hidden animate-slide-in hover:border-[#111113] transition-colors",
        isOverdue ? "border-amber-300" : "border-[#d0cec9]",
      )}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-[#fafaf8] transition-colors text-left"
      >
        <span
          className={cn(
            "flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded border shrink-0",
            typeStyles,
          )}
        >
          <TypeIcon className="w-3 h-3" />
          {isRetest ? "Retest" : "Transfer"}
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[#111113] truncate">
            {task.question.text}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-[#9e9eae]">
              {task.question.question_type === "MCQ" ? "Multiple choice" : "Short answer"}
            </span>
            <span className="text-[#d0cec9]">·</span>
            <span className={cn("text-xs font-medium", isOverdue ? "text-amber-700" : "text-[#9e9eae]")}>
              {formatRelativeTime(task.due_at)}
            </span>
          </div>
        </div>

        <span className="text-[#9e9eae] shrink-0">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-[#ece9e4] px-5 py-5 bg-[#fafaf8]">
          <p className="text-sm text-[#111113] font-medium mb-4 leading-relaxed">
            {task.question.text}
          </p>
          <AttemptPanel
            question={task.question}
            studentId={studentId}
            onSuccess={() => setExpanded(false)}
          />
        </div>
      )}
    </div>
  );
}
