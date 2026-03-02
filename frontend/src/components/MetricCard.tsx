"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn, getMetricColor, getMetricBarColor } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  score: number;
  explanation: string;
  icon: React.ReactNode;
  sublabel?: string;
}

export default function MetricCard({
  label,
  score,
  explanation,
  icon,
  sublabel,
}: MetricCardProps) {
  const [expanded, setExpanded] = useState(false);
  const rounded = Math.round(score);
  const colorClass = getMetricColor(score);
  const barColor = getMetricBarColor(score);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5 flex flex-col gap-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{icon}</span>
          <span className="text-sm font-semibold text-gray-600">{label}</span>
        </div>
        <span className={cn("text-2xl font-bold tabular-nums", colorClass)}>
          {rounded}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", barColor)}
          style={{ width: `${Math.max(2, rounded)}%` }}
        />
      </div>

      {sublabel && (
        <p className="text-xs text-gray-400">{sublabel}</p>
      )}

      {/* Collapsible explanation */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors w-fit"
      >
        {expanded ? (
          <>
            <ChevronUp className="w-3 h-3" />
            Hide explanation
          </>
        ) : (
          <>
            <ChevronDown className="w-3 h-3" />
            Why this score?
          </>
        )}
      </button>

      {expanded && (
        <p className="text-xs text-gray-500 leading-relaxed border-t border-gray-100 pt-2 animate-fade-in">
          {explanation}
        </p>
      )}
    </div>
  );
}
