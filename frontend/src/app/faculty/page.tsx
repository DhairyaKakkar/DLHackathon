"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  LogOut,
  User,
  Bot,
} from "lucide-react";
import { getFacultyDashboard, getStudents } from "@/lib/api";
import { getAuth, clearAuth } from "@/lib/auth";
import DUSHistogram from "@/components/DUSHistogram";
import { FacultySkeleton } from "@/components/Skeletons";
import ErrorState from "@/components/ErrorState";
import Navbar from "@/components/Navbar";
import { cn, getMetricColor, getMetricBarColor } from "@/lib/utils";

function StatCard({ label, value, icon: Icon, iconColor }: { label: string; value: string | number; icon: React.ComponentType<{ className?: string }>; iconColor: string }) {
  return (
    <div className="bg-white/[0.04] rounded-xl border border-white/[0.08] shadow-card p-5 hover:border-white/[0.14] transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          {label}
        </span>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function RiskCard({
  title,
  topics,
  icon: Icon,
  iconGlow,
  iconColor,
  badgeBg,
  badgeText,
  badgeBorder,
  emptyMsg,
}: {
  title: string;
  topics: string[];
  icon: React.ComponentType<{ className?: string }>;
  iconGlow: string;
  iconColor: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  emptyMsg: string;
}) {
  return (
    <div className="bg-white/[0.04] rounded-xl border border-white/[0.08] shadow-card p-5 hover:border-white/[0.14] transition-colors">
      <div className="flex items-center gap-2 mb-3">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ background: iconGlow, border: `1px solid ${iconGlow.replace("15", "30")}` }}
        >
          <Icon className={`w-4 h-4 ${iconColor}`} />
        </div>
        <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      </div>
      {topics.length === 0 ? (
        <p className="text-xs text-slate-600 italic">{emptyMsg}</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {topics.map((t) => (
            <span
              key={t}
              className={`text-xs font-medium px-2 py-0.5 rounded-full border ${badgeBg} ${badgeText} ${badgeBorder}`}
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
      <div className="flex-1 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", getMetricBarColor(value))}
          style={{ width: `${Math.max(2, value)}%` }}
        />
      </div>
      <span className={cn("text-xs tabular-nums font-semibold w-7 text-right", getMetricColor(value))}>
        {Math.round(value)}
      </span>
    </div>
  );
}

export default function FacultyDashboardPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const a = getAuth();
    if (!a) { router.replace("/login"); return; }
    if (a.role !== "faculty") { router.replace(`/student/${a.studentId}`); return; }
    setChecking(false);
  }, [router]);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["facultyDashboard"],
    queryFn: getFacultyDashboard,
    staleTime: 60_000,
    enabled: !checking,
  });

  const { data: students } = useQuery({
    queryKey: ["students"],
    queryFn: getStudents,
    staleTime: 300_000,
    enabled: !checking,
  });

  // Only show students (not faculty accounts)
  const studentList = (students ?? []).filter((s: { role: string }) => s.role === "student");

  function handleSignOut() {
    clearAuth();
    router.replace("/login");
  }

  if (checking) return null;

  return (
    <div className="min-h-screen bg-[#09090f]">
      <Navbar
        title="Faculty Dashboard"
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.06] transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={handleSignOut}
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors px-2 py-2 rounded-lg hover:bg-white/[0.06]"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        }
      />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {isLoading && <FacultySkeleton />}
        {isError && <ErrorState message={(error as Error)?.message} onRetry={() => refetch()} />}

        {data && (
          <div className="flex flex-col gap-6 animate-fade-in">
            {/* Header */}
            <div>
              <h1 className="font-display text-2xl font-bold text-white">
                Cohort Analytics
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                {data.explanation}
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <StatCard label="Students" value={data.num_students} icon={Users} iconColor="text-indigo-400" />
              <StatCard label="Topics" value={data.num_topics} icon={BookOpen} iconColor="text-blue-400" />
              <StatCard
                label="Avg DUS"
                value={data.topic_summaries.length > 0 ? Math.round(data.topic_summaries.reduce((s: number, t: { avg_dus: number }) => s + t.avg_dus, 0) / data.topic_summaries.length) : "—"}
                icon={BarChart3}
                iconColor="text-emerald-400"
              />
            </div>

            {/* Risk cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <RiskCard
                title="Low Retention Topics"
                topics={data.low_retention_topics}
                icon={TrendingDown}
                iconGlow="rgba(244,63,94,0.15)"
                iconColor="text-red-400"
                badgeBg="bg-red-500/10"
                badgeText="text-red-400"
                badgeBorder="border-red-500/25"
                emptyMsg="No low-retention topics — great!"
              />
              <RiskCard
                title="Transfer Failures"
                topics={data.transfer_failure_topics}
                icon={Shuffle}
                iconGlow="rgba(139,92,246,0.15)"
                iconColor="text-violet-400"
                badgeBg="bg-violet-500/10"
                badgeText="text-violet-400"
                badgeBorder="border-violet-500/25"
                emptyMsg="No transfer failures — great!"
              />
              <RiskCard
                title="Overconfidence Hotspots"
                topics={data.overconfidence_hotspots}
                icon={Target}
                iconGlow="rgba(245,158,11,0.15)"
                iconColor="text-amber-400"
                badgeBg="bg-amber-500/10"
                badgeText="text-amber-400"
                badgeBorder="border-amber-500/25"
                emptyMsg="No overconfidence hotspots — great!"
              />
              <RiskCard
                title="AI Dependency Risk"
                topics={data.ai_risk_students ?? []}
                icon={Bot}
                iconGlow="rgba(249,115,22,0.15)"
                iconColor="text-orange-400"
                badgeBg="bg-orange-500/10"
                badgeText="text-orange-400"
                badgeBorder="border-orange-500/25"
                emptyMsg="No AI-dependency risk detected — great!"
              />
            </div>

            {/* DUS histogram */}
            <div className="bg-white/[0.04] rounded-xl border border-white/[0.08] shadow-card p-6">
              <div className="flex items-center gap-2 mb-1">
                <BarChart3 className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-slate-300">
                  DUS Distribution
                </h2>
              </div>
              <p className="text-xs text-slate-600 mb-4">
                Number of student × topic pairs at each score range
              </p>
              <DUSHistogram data={data.dus_distribution} />
              <div className="flex flex-wrap gap-4 mt-4 justify-center">
                {[
                  { color: "#f43f5e", label: "Fragile (< 60)" },
                  { color: "#f59e0b", label: "Partial (60–79)" },
                  { color: "#10b981", label: "Durable (≥ 80)" },
                ].map(({ color, label }) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <div
                      className="w-3 h-3 rounded-sm"
                      style={{ backgroundColor: color, opacity: 0.85 }}
                    />
                    <span className="text-xs text-slate-500">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Topic summary table */}
            <div className="bg-white/[0.04] rounded-xl border border-white/[0.08] shadow-card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-300">
                  Topic Breakdown
                </h2>
                <span className="text-xs text-slate-600">
                  Across {data.num_students} student{data.num_students !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] bg-white/[0.03]">
                      {["Topic", "Students", "Avg Mastery", "Avg Retention", "Avg Transfer", "Avg Calibration", "Avg DUS", "Flags"].map(
                        (h) => (
                          <th
                            key={h}
                            className="text-left px-4 py-3 font-semibold text-slate-500 text-xs uppercase tracking-wide"
                          >
                            {h}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {data.topic_summaries.map((t: {
                      topic_id: number;
                      topic_name: string;
                      num_students: number;
                      avg_mastery: number;
                      avg_retention: number;
                      avg_transfer: number;
                      avg_calibration: number;
                      avg_dus: number;
                      low_retention_flag: boolean;
                      transfer_failure_flag: boolean;
                      overconfidence_flag: boolean;
                      ai_dependency_flag?: boolean;
                    }, i: number) => (
                      <tr
                        key={t.topic_id}
                        className={cn(
                          "border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors",
                          i === data.topic_summaries.length - 1 && "border-b-0",
                        )}
                      >
                        <td className="px-4 py-3.5 font-medium text-slate-200">
                          {t.topic_name}
                        </td>
                        <td className="px-4 py-3.5 text-slate-500">
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
                              <span className="text-xs bg-red-500/10 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded-full">
                                retention
                              </span>
                            )}
                            {t.transfer_failure_flag && (
                              <span className="text-xs bg-violet-500/10 text-violet-400 border border-violet-500/20 px-1.5 py-0.5 rounded-full">
                                transfer
                              </span>
                            )}
                            {t.overconfidence_flag && (
                              <span className="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded-full">
                                overconf
                              </span>
                            )}
                            {t.ai_dependency_flag && (
                              <span className="text-xs bg-orange-500/10 text-orange-400 border border-orange-500/20 px-1.5 py-0.5 rounded-full">
                                ai-risk
                              </span>
                            )}
                            {!t.low_retention_flag &&
                              !t.transfer_failure_flag &&
                              !t.overconfidence_flag &&
                              !t.ai_dependency_flag && (
                                <span className="text-xs text-slate-700">—</span>
                              )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Individual student dashboards — dynamic list */}
            {studentList.length > 0 && (
              <div className="bg-indigo-500/[0.06] border border-indigo-500/20 rounded-xl p-5">
                <p className="text-sm font-semibold text-indigo-300 mb-3">
                  View individual student dashboards
                </p>
                <div className="flex flex-wrap gap-2">
                  {studentList.map((s: { id: number; name: string }) => (
                    <Link
                      key={s.id}
                      href={`/student/${s.id}`}
                      className="flex items-center gap-2 bg-white/[0.04] border border-indigo-500/25 text-indigo-300 text-sm font-medium px-3 py-2 rounded-lg hover:bg-indigo-600 hover:text-white hover:border-indigo-600 transition-all"
                    >
                      <User className="w-3.5 h-3.5" />
                      {s.name}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
