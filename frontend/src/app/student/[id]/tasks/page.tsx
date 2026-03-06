"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, CheckCircle, CalendarClock, LogOut } from "lucide-react";
import { getStudentTasks, getStudentDashboard } from "@/lib/api";
import { getAuth, clearAuth, type EaleAuth } from "@/lib/auth";
import TaskCard from "@/components/TaskCard";
import { TasksSkeleton } from "@/components/Skeletons";
import ErrorState from "@/components/ErrorState";
import Navbar from "@/components/Navbar";
import DUSGauge from "@/components/DUSGauge";
import { getDusTextClass } from "@/lib/utils";

export default function StudentTasksPage() {
  const params = useParams();
  const router = useRouter();
  const studentId = Number(params.id);
  const [includeFuture, setIncludeFuture] = useState(false);
  const [auth, setAuthState] = useState<EaleAuth | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const a = getAuth();
    if (!a) { router.replace("/login"); return; }
    if (a.role === "student" && a.studentId !== studentId) {
      router.replace(`/student/${a.studentId}`);
      return;
    }
    setAuthState(a);
    setChecking(false);
  }, [studentId, router]);

  const tasksQuery = useQuery({
    queryKey: ["tasks", studentId, includeFuture],
    queryFn: () => getStudentTasks(studentId, includeFuture),
    enabled: !isNaN(studentId) && !checking,
    refetchInterval: 30_000,
  });

  const dashQuery = useQuery({
    queryKey: ["studentDashboard", studentId],
    queryFn: () => getStudentDashboard(studentId),
    enabled: !isNaN(studentId) && !checking,
  });

  const tasks = tasksQuery.data ?? [];
  const dashboard = dashQuery.data;

  function handleSignOut() {
    clearAuth();
    router.replace("/login");
  }

  if (checking) return null;

  return (
    <div className="min-h-screen bg-[#fafaf8]">
      <Navbar
        backHref={`/student/${studentId}`}
        backLabel="Dashboard"
        title={dashboard?.student_name ? `${dashboard.student_name} — Tasks` : "Tasks"}
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => tasksQuery.refetch()}
              disabled={tasksQuery.isFetching}
              className="p-2 rounded-lg text-[#9e9eae] hover:text-[#111113] hover:bg-black/[0.04] transition-colors"
              title="Refresh tasks"
            >
              <RefreshCw className={`w-4 h-4 ${tasksQuery.isFetching ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={handleSignOut}
              className="flex items-center gap-1.5 text-sm text-[#9e9eae] hover:text-[#111113] transition-colors px-2 py-2 rounded-lg hover:bg-black/[0.04]"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        }
      />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col gap-6">
          {/* Mini dashboard strip */}
          {dashboard && (
            <div className="bg-white rounded-xl border border-[#d0cec9] shadow-card p-4 flex items-center gap-5 animate-fade-in">
              <DUSGauge score={dashboard.overall_dus} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[#111113]">
                  {dashboard.student_name}
                </p>
                <p className="text-xs text-[#5c5c6e] mt-0.5">
                  Overall DUS:{" "}
                  <span className={`font-bold font-mono ${getDusTextClass(dashboard.overall_dus)}`}>
                    {Math.round(dashboard.overall_dus)}
                  </span>
                </p>
                {dashboard.topics.length > 0 && (
                  <p className="text-xs text-[#9e9eae] mt-0.5">
                    {dashboard.topics.length} topics tracked
                  </p>
                )}
              </div>
              <Link
                href={`/student/${studentId}`}
                className="text-xs text-[#e8325a] font-semibold hover:text-[#c41f47] transition-colors shrink-0"
              >
                Full dashboard →
              </Link>
            </div>
          )}

          {/* Tasks header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display italic text-xl font-bold text-[#111113] flex items-center gap-2">
                <CalendarClock className="w-5 h-5 text-[#e8325a]" />
                Due Tasks
                {!tasksQuery.isLoading && (
                  <span className="text-base font-normal font-sans not-italic text-[#9e9eae]">
                    ({tasks.length})
                  </span>
                )}
              </h1>
              <p className="text-xs text-[#9e9eae] mt-0.5">
                Complete retests and transfer exercises to update your scores
              </p>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-[#9e9eae]">Show future</span>
              <button
                onClick={() => setIncludeFuture((v) => !v)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  includeFuture ? "bg-[#111113]" : "bg-black/[0.1]"
                }`}
              >
                <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${includeFuture ? "translate-x-4" : "translate-x-1"}`} />
              </button>
            </label>
          </div>

          {tasksQuery.isLoading && <TasksSkeleton />}
          {tasksQuery.isError && <ErrorState message={(tasksQuery.error as Error)?.message} onRetry={() => tasksQuery.refetch()} />}

          {!tasksQuery.isLoading && !tasksQuery.isError && tasks.length === 0 && (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center">
                <CheckCircle className="w-7 h-7 text-emerald-600" />
              </div>
              <div>
                <p className="font-semibold text-[#111113]">All caught up!</p>
                <p className="text-sm text-[#5c5c6e] mt-1">
                  {includeFuture
                    ? "No tasks scheduled at all."
                    : "No tasks are due right now. Toggle 'Show future' to see upcoming tasks."}
                </p>
              </div>
              {!includeFuture && (
                <button
                  onClick={() => setIncludeFuture(true)}
                  className="text-sm text-[#e8325a] font-semibold hover:text-[#c41f47] transition-colors"
                >
                  Show future tasks →
                </button>
              )}
            </div>
          )}

          {tasks.length > 0 && (
            <div className="flex flex-col gap-3">
              {tasks.map((task, i) => (
                <TaskCard key={task.id} task={task} studentId={studentId} index={i} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
