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
  const [expanded, setExpanded] = useState(index === 0); // open first by default

  const isOverdue = new Date(task.due_at) < new Date();
  const isRetest = task.task_type === "RETEST";

  const typeStyles = isRetest
    ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
    : "bg-violet-500/10 text-violet-400 border-violet-500/20";

  const TypeIcon = isRetest ? RotateCcw : Shuffle;

  return (
    <div
      className={cn(
        "bg-white/[0.04] rounded-xl border shadow-card overflow-hidden animate-slide-in hover:border-white/[0.14] transition-colors",
        isOverdue ? "border-amber-500/30" : "border-white/[0.08]",
      )}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-white/[0.03] transition-colors text-left"
      >
        {/* Task type badge */}
        <span
          className={cn(
            "flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border shrink-0",
            typeStyles,
          )}
        >
          <TypeIcon className="w-3 h-3" />
          {isRetest ? "Retest" : "Transfer"}
        </span>

        {/* Question preview */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">
            {task.question.text}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-slate-600">
              {task.question.question_type === "MCQ" ? "Multiple choice" : "Short answer"}
            </span>
            <span className="text-white/10">·</span>
            <span
              className={cn(
                "text-xs font-medium",
                isOverdue ? "text-amber-400" : "text-slate-500",
              )}
            >
              {formatRelativeTime(task.due_at)}
            </span>
          </div>
        </div>

        {/* Expand toggle */}
        <span className="text-slate-600 shrink-0">
          {expanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </span>
      </button>

      {/* Expanded attempt form */}
      {expanded && (
        <div className="border-t border-white/[0.06] px-5 py-5 bg-white/[0.02]">
          {/* Full question text */}
          <p className="text-sm text-slate-200 font-medium mb-4 leading-relaxed">
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
