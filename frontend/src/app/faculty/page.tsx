"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  TrendingDown,
  Shuffle,
  Target,
  Users,
  BookOpen,
  BarChart3,
  RefreshCw,
} from "lucide-react";
import { getFacultyDashboard } from "@/lib/api";
import DUSHistogram from "@/components/DUSHistogram";
import { FacultySkeleton } from "@/components/Skeletons";
import ErrorState from "@/components/ErrorState";
import Navbar from "@/components/Navbar";
import { cn, getMetricColor, getMetricBarColor } from "@/lib/utils";

function StatCard({
  label,
  value,
  icon: Icon,
  iconColor,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          {label}
        </span>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

function RiskCard({
  title,
  topics,
  icon: Icon,
  iconBg,
  iconColor,
  emptyMsg,
}: {
  title: string;
  topics: string[];
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  emptyMsg: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-7 h-7 rounded-lg ${iconBg} flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${iconColor}`} />
        </div>
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>

      {topics.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{emptyMsg}</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {topics.map((t) => (
            <span
              key={t}
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${iconBg} ${iconColor} border`}
              style={{
                borderColor: iconColor.includes("red")
                  ? "#fecaca"
                  : iconColor.includes("amber")
                    ? "#fde68a"
                    : "#c4b5fd",
              }}
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", getMetricBarColor(value))}
          style={{ width: `${Math.max(2, value)}%` }}
        />
      </div>
      <span
        className={cn("text-xs tabular-nums font-semibold w-7 text-right", getMetricColor(value))}
      >
        {Math.round(value)}
      </span>
    </div>
  );
}

export default function FacultyDashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["facultyDashboard"],
    queryFn: getFacultyDashboard,
    staleTime: 60_000,
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar
        backHref="/"
        backLabel="Home"
        title="Faculty Dashboard"
        action={
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
          </button>
        }
      />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {isLoading && <FacultySkeleton />}

        {isError && (
          <ErrorState
            message={(error as Error)?.message}
            onRetry={() => refetch()}
          />
        )}

        {data && (
          <div className="flex flex-col gap-6 animate-fade-in">
            {/* Header */}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Cohort Analytics
              </h1>
              <p className="text-sm text-gray-400 mt-0.5">
                {data.explanation}
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <StatCard
                label="Students"
                value={data.num_students}
                icon={Users}
                iconColor="text-indigo-400"
              />
              <StatCard
                label="Topics"
                value={data.num_topics}
                icon={BookOpen}
                iconColor="text-blue-400"
              />
              <StatCard
                label="Avg DUS"
                value={
                  data.topic_summaries.length > 0
                    ? Math.round(
                        data.topic_summaries.reduce(
                          (s, t) => s + t.avg_dus,
                          0,
                        ) / data.topic_summaries.length,
                      )
                    : "—"
                }
                icon={BarChart3}
                iconColor="text-green-400"
              />
            </div>

            {/* Risk cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <RiskCard
                title="Low Retention Topics"
                topics={data.low_retention_topics}
                icon={TrendingDown}
                iconBg="bg-red-50"
                iconColor="text-red-500"
                emptyMsg="No low-retention topics — great!"
              />
              <RiskCard
                title="Transfer Failures"
                topics={data.transfer_failure_topics}
                icon={Shuffle}
                iconBg="bg-purple-50"
                iconColor="text-purple-500"
                emptyMsg="No transfer failures — great!"
              />
              <RiskCard
                title="Overconfidence Hotspots"
                topics={data.overconfidence_hotspots}
                icon={Target}
                iconBg="bg-amber-50"
                iconColor="text-amber-500"
                emptyMsg="No overconfidence hotspots — great!"
              />
            </div>

            {/* DUS histogram */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-card p-6">
              <div className="flex items-center gap-2 mb-1">
                <BarChart3 className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-gray-700">
                  DUS Distribution
                </h2>
              </div>
              <p className="text-xs text-gray-400 mb-4">
                Number of student × topic pairs at each score range
              </p>
              <DUSHistogram data={data.dus_distribution} />

              {/* Legend */}
              <div className="flex flex-wrap gap-4 mt-4 justify-center">
                {[
                  { color: "#ef4444", label: "Fragile (< 60)" },
                  { color: "#f59e0b", label: "Partial (60–79)" },
                  { color: "#22c55e", label: "Durable (≥ 80)" },
                ].map(({ color, label }) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <div
                      className="w-3 h-3 rounded-sm"
                      style={{ backgroundColor: color, opacity: 0.85 }}
                    />
                    <span className="text-xs text-gray-500">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Topic summary table */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700">
                  Topic Breakdown
                </h2>
                <span className="text-xs text-gray-400">
                  Across {data.num_students} student{data.num_students !== 1 ? "s" : ""}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50/60">
                      {["Topic", "Students", "Avg Mastery", "Avg Retention", "Avg Transfer", "Avg Calibration", "Avg DUS", "Flags"].map(
                        (h) => (
                          <th
                            key={h}
                            className="text-left px-4 py-3 font-semibold text-gray-400 text-xs uppercase tracking-wide"
                          >
                            {h}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {data.topic_summaries.map((t, i) => (
                      <tr
                        key={t.topic_id}
                        className={cn(
                          "border-b border-gray-50 hover:bg-gray-50/50 transition-colors",
                          i === data.topic_summaries.length - 1 && "border-b-0",
                        )}
                      >
                        <td className="px-4 py-3.5 font-medium text-gray-800">
                          {t.topic_name}
                        </td>
                        <td className="px-4 py-3.5 text-gray-500">
                          {t.num_students}
                        </td>
                        <td className="px-4 py-3.5">
                          <MetricBar value={t.avg_mastery} />
                        </td>
                        <td className="px-4 py-3.5">
                          <MetricBar value={t.avg_retention} />
                        </td>
                        <td className="px-4 py-3.5">
                          <MetricBar value={t.avg_transfer} />
                        </td>
                        <td className="px-4 py-3.5">
                          <MetricBar value={t.avg_calibration} />
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={cn(
                              "text-base font-bold tabular-nums",
                              getMetricColor(t.avg_dus),
                            )}
                          >
                            {Math.round(t.avg_dus)}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap gap-1">
                            {t.low_retention_flag && (
                              <span className="text-xs bg-red-50 text-red-600 border border-red-100 px-1.5 py-0.5 rounded-full">
                                retention
                              </span>
                            )}
                            {t.transfer_failure_flag && (
                              <span className="text-xs bg-purple-50 text-purple-600 border border-purple-100 px-1.5 py-0.5 rounded-full">
                                transfer
                              </span>
                            )}
                            {t.overconfidence_flag && (
                              <span className="text-xs bg-amber-50 text-amber-600 border border-amber-100 px-1.5 py-0.5 rounded-full">
                                overconf
                              </span>
                            )}
                            {!t.low_retention_flag &&
                              !t.transfer_failure_flag &&
                              !t.overconfidence_flag && (
                                <span className="text-xs text-gray-300">—</span>
                              )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick links to student views */}
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
              <p className="text-sm font-semibold text-indigo-800 mb-3">
                View individual student dashboards
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: 1, name: "Alice Chen", tag: "Fragile Mastery" },
                  { id: 2, name: "Bob Martinez", tag: "Overconfident" },
                ].map(({ id, name, tag }) => (
                  <Link
                    key={id}
                    href={`/student/${id}`}
                    className="flex items-center gap-2 bg-white border border-indigo-200 text-indigo-700 text-sm font-medium px-3 py-2 rounded-lg hover:bg-indigo-600 hover:text-white hover:border-indigo-600 transition-all"
                  >
                    {name}
                    <span className="text-xs opacity-60">({tag})</span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
