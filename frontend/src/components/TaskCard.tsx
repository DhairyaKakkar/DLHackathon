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
    ? "bg-blue-50 text-blue-700 border-blue-200"
    : "bg-purple-50 text-purple-700 border-purple-200";

  const TypeIcon = isRetest ? RotateCcw : Shuffle;

  return (
    <div
      className={cn(
        "bg-white rounded-xl border shadow-card overflow-hidden animate-slide-in",
        isOverdue ? "border-amber-200" : "border-gray-200",
      )}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-gray-50/60 transition-colors text-left"
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
          <p className="text-sm font-medium text-gray-800 truncate">
            {task.question.text}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-gray-400">
              {task.question.question_type === "MCQ" ? "Multiple choice" : "Short answer"}
            </span>
            <span className="text-gray-200">·</span>
            <span
              className={cn(
                "text-xs font-medium",
                isOverdue ? "text-amber-600" : "text-gray-400",
              )}
            >
              {formatRelativeTime(task.due_at)}
            </span>
          </div>
        </div>

        {/* Expand toggle */}
        <span className="text-gray-300 shrink-0">
          {expanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </span>
      </button>

      {/* Expanded attempt form */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-5 bg-gray-50/30">
          {/* Full question text */}
          <p className="text-sm text-gray-800 font-medium mb-4 leading-relaxed">
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
