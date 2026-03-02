"use client";

import Link from "next/link";
import {
  cn,
  getDusBadgeClass,
  getDusLabel,
  getDusTextClass,
  getTopRisk,
  getMetricBarColor,
} from "@/lib/utils";
import type { TopicMetrics } from "@/lib/types";

interface TopicTableProps {
  topics: TopicMetrics[];
  studentId: number;
}

function MiniBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 bg-white/[0.08] rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", getMetricBarColor(value))}
          style={{ width: `${Math.max(2, value)}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-slate-500 w-6">
        {Math.round(value)}
      </span>
    </div>
  );
}

export default function TopicTable({ topics, studentId }: TopicTableProps) {
  if (topics.length === 0) {
    return (
      <div className="bg-white/[0.04] rounded-xl border border-white/[0.08] p-8 text-center text-slate-500 text-sm">
        No topic data yet.
      </div>
    );
  }

  return (
    <div className="bg-white/[0.04] rounded-xl border border-white/[0.08] shadow-card overflow-hidden animate-fade-in">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06] bg-white/[0.03]">
              <th className="text-left px-5 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide">
                Topic
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide">
                DUS
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide hidden md:table-cell">
                Mastery
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide hidden md:table-cell">
                Retention
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide hidden lg:table-cell">
                Transfer
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide">
                Top Risk
              </th>
            </tr>
          </thead>
          <tbody>
            {topics.map((t, i) => {
              const risk = getTopRisk(t);
              return (
                <tr
                  key={t.topic_id}
                  className={cn(
                    "border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors",
                    i === topics.length - 1 && "border-b-0",
                  )}
                >
                  <td className="px-5 py-3.5 font-medium text-slate-200">
                    {t.topic_name}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "text-base font-bold tabular-nums",
                          getDusTextClass(t.durable_understanding_score),
                        )}
                      >
                        {Math.round(t.durable_understanding_score)}
                      </span>
                      <span
                        className={cn(
                          "text-xs px-1.5 py-0.5 rounded-md font-medium",
                          getDusBadgeClass(t.durable_understanding_score),
                        )}
                      >
                        {getDusLabel(t.durable_understanding_score)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 hidden md:table-cell">
                    <MiniBar value={t.mastery} />
                  </td>
                  <td className="px-4 py-3.5 hidden md:table-cell">
                    <MiniBar value={t.retention} />
                  </td>
                  <td className="px-4 py-3.5 hidden lg:table-cell">
                    <MiniBar value={t.transfer_robustness} />
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full font-medium">
                      ⚠ {risk}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
