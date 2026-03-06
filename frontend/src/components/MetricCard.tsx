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
    <div className="bg-white rounded-xl border border-[#d0cec9] shadow-card p-5 flex flex-col gap-3 animate-fade-in hover:border-[#111113] transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[#9e9eae]">{icon}</span>
          <span className="text-sm font-semibold text-[#5c5c6e]">{label}</span>
        </div>
        <span className={cn("text-2xl font-bold tabular-nums font-mono", colorClass)}>
          {rounded}
        </span>
      </div>

      <div className="h-1 bg-black/[0.06] rounded-none overflow-hidden">
        <div
          className={cn("h-full transition-all duration-700", barColor)}
          style={{ width: `${Math.max(2, rounded)}%` }}
        />
      </div>

      {sublabel && (
        <p className="text-xs text-[#9e9eae]">{sublabel}</p>
      )}

      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-1 text-xs text-[#9e9eae] hover:text-[#5c5c6e] transition-colors w-fit"
      >
        {expanded ? (
          <><ChevronUp className="w-3 h-3" />Hide explanation</>
        ) : (
          <><ChevronDown className="w-3 h-3" />Why this score?</>
        )}
      </button>

      {expanded && (
        <p className="text-xs text-[#5c5c6e] leading-relaxed border-t border-[#ece9e4] pt-2 animate-fade-in">
          {explanation}
        </p>
      )}
    </div>
  );
}
