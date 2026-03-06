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
      <div className="h-1 w-20 bg-black/[0.06] overflow-hidden">
        <div
          className={cn("h-full", getMetricBarColor(value))}
          style={{ width: `${Math.max(2, value)}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-[#9e9eae] w-6 font-mono">
        {Math.round(value)}
      </span>
    </div>
  );
}

export default function TopicTable({ topics, studentId }: TopicTableProps) {
  if (topics.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[#d0cec9] p-8 text-center text-[#9e9eae] text-sm">
        No topic data yet.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[#d0cec9] shadow-card overflow-hidden animate-fade-in">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#ece9e4] bg-[#f4f3f0]">
              <th className="text-left px-5 py-3 font-semibold text-[#9e9eae] text-xs uppercase tracking-wide">
                Topic
              </th>
              <th className="text-left px-4 py-3 font-semibold text-[#9e9eae] text-xs uppercase tracking-wide">
                DUS
              </th>
              <th className="text-left px-4 py-3 font-semibold text-[#9e9eae] text-xs uppercase tracking-wide hidden md:table-cell">
                Mastery
              </th>
              <th className="text-left px-4 py-3 font-semibold text-[#9e9eae] text-xs uppercase tracking-wide hidden md:table-cell">
                Retention
              </th>
              <th className="text-left px-4 py-3 font-semibold text-[#9e9eae] text-xs uppercase tracking-wide hidden lg:table-cell">
                Transfer
              </th>
              <th className="text-left px-4 py-3 font-semibold text-[#9e9eae] text-xs uppercase tracking-wide">
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
                    "border-b border-[#ece9e4] hover:bg-[#fafaf8] transition-colors",
                    i === topics.length - 1 && "border-b-0",
                  )}
                >
                  <td className="px-5 py-3.5 font-medium text-[#111113]">
                    {t.topic_name}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "text-base font-bold tabular-nums font-mono",
                          getDusTextClass(t.durable_understanding_score),
                        )}
                      >
                        {Math.round(t.durable_understanding_score)}
                      </span>
                      <span
                        className={cn(
                          "text-xs px-1.5 py-0.5 rounded font-medium",
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
                    <span className="inline-flex items-center gap-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded font-medium">
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
