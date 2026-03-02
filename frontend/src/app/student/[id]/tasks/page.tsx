"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, CheckCircle, CalendarClock } from "lucide-react";
import { getStudentTasks, getStudentDashboard } from "@/lib/api";
import TaskCard from "@/components/TaskCard";
import { TasksSkeleton } from "@/components/Skeletons";
import ErrorState from "@/components/ErrorState";
import Navbar from "@/components/Navbar";
import DUSGauge from "@/components/DUSGauge";
import { getDusTextClass } from "@/lib/utils";

export default function StudentTasksPage() {
  const params = useParams();
  const studentId = Number(params.id);
  const [includeFuture, setIncludeFuture] = useState(false);

  const tasksQuery = useQuery({
    queryKey: ["tasks", studentId, includeFuture],
    queryFn: () => getStudentTasks(studentId, includeFuture),
    enabled: !isNaN(studentId),
    refetchInterval: 30_000,
  });

  const dashQuery = useQuery({
    queryKey: ["studentDashboard", studentId],
    queryFn: () => getStudentDashboard(studentId),
    enabled: !isNaN(studentId),
  });

  const tasks = tasksQuery.data ?? [];
  const dashboard = dashQuery.data;

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar
        backHref={`/student/${studentId}`}
        backLabel="Dashboard"
        title={dashboard?.student_name ? `${dashboard.student_name} — Tasks` : "Tasks"}
        action={
          <button
            onClick={() => tasksQuery.refetch()}
            disabled={tasksQuery.isFetching}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            title="Refresh tasks"
          >
            <RefreshCw
              className={`w-4 h-4 ${tasksQuery.isFetching ? "animate-spin" : ""}`}
            />
          </button>
        }
      />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col gap-6">
          {/* Mini dashboard strip */}
          {dashboard && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4 flex items-center gap-5 animate-fade-in">
              <DUSGauge score={dashboard.overall_dus} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800">
                  {dashboard.student_name}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Overall DUS:{" "}
                  <span
                    className={`font-bold ${getDusTextClass(dashboard.overall_dus)}`}
                  >
                    {Math.round(dashboard.overall_dus)}
                  </span>
                </p>
                {dashboard.topics.length > 0 && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {dashboard.topics.length} topics tracked
                  </p>
                )}
              </div>
              <Link
                href={`/student/${studentId}`}
                className="text-xs text-indigo-600 font-semibold hover:underline shrink-0"
              >
                Full dashboard →
              </Link>
            </div>
          )}

          {/* Tasks header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <CalendarClock className="w-5 h-5 text-indigo-500" />
                Due Tasks
                {!tasksQuery.isLoading && (
                  <span className="text-base font-normal text-gray-400">
                    ({tasks.length})
                  </span>
                )}
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Complete retests and transfer exercises to update your scores
              </p>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-gray-500">Show future</span>
              <button
                onClick={() => setIncludeFuture((v) => !v)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  includeFuture ? "bg-indigo-600" : "bg-gray-200"
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                    includeFuture ? "translate-x-4" : "translate-x-1"
                  }`}
                />
              </button>
            </label>
          </div>

          {/* Loading */}
          {tasksQuery.isLoading && <TasksSkeleton />}

          {/* Error */}
          {tasksQuery.isError && (
            <ErrorState
              message={(tasksQuery.error as Error)?.message}
              onRetry={() => tasksQuery.refetch()}
            />
          )}

          {/* Empty state */}
          {!tasksQuery.isLoading && !tasksQuery.isError && tasks.length === 0 && (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <div className="w-14 h-14 rounded-full bg-green-50 flex items-center justify-center">
                <CheckCircle className="w-7 h-7 text-green-400" />
              </div>
              <div>
                <p className="font-semibold text-gray-700">All caught up!</p>
                <p className="text-sm text-gray-400 mt-1">
                  {includeFuture
                    ? "No tasks scheduled at all."
                    : "No tasks are due right now. Toggle 'Show future' to see upcoming tasks."}
                </p>
              </div>
              {!includeFuture && (
                <button
                  onClick={() => setIncludeFuture(true)}
                  className="text-sm text-indigo-600 font-semibold hover:underline"
                >
                  Show future tasks →
                </button>
              )}
            </div>
          )}

          {/* Task list */}
          {tasks.length > 0 && (
            <div className="flex flex-col gap-3">
              {tasks.map((task, i) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  studentId={studentId}
                  index={i}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
