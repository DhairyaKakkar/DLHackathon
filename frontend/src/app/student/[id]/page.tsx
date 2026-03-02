"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Clock,
  Shuffle,
  Target,
  BarChart3,
  ClipboardList,
  Info,
} from "lucide-react";
import { getStudentDashboard } from "@/lib/api";
import {
  getDusTextClass,
  getDusBg,
  getDusLabel,
} from "@/lib/utils";
import DUSGauge from "@/components/DUSGauge";
import MetricCard from "@/components/MetricCard";
import TopicTable from "@/components/TopicTable";
import { StudentDashboardSkeleton } from "@/components/Skeletons";
import ErrorState from "@/components/ErrorState";
import Navbar from "@/components/Navbar";

function Tooltip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <Info className="w-3.5 h-3.5 text-gray-300 hover:text-gray-500 cursor-help" />
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-52 bg-gray-900 text-white text-xs rounded-lg px-2.5 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity leading-snug z-30">
        {text}
      </span>
    </span>
  );
}

export default function StudentDashboardPage() {
  const params = useParams();
  const studentId = Number(params.id);

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["studentDashboard", studentId],
    queryFn: () => getStudentDashboard(studentId),
    enabled: !isNaN(studentId),
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar
        backHref="/"
        backLabel="Home"
        title={data?.student_name}
        action={
          <Link
            href={`/student/${studentId}/tasks`}
            className="flex items-center gap-1.5 bg-indigo-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <ClipboardList className="w-4 h-4" />
            Tasks
          </Link>
        }
      />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {isLoading && <StudentDashboardSkeleton />}

        {isError && (
          <ErrorState
            message={(error as Error)?.message}
            onRetry={() => refetch()}
          />
        )}

        {data && (
          <div className="flex flex-col gap-6 animate-fade-in">
            {/* Page header */}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {data.student_name}
              </h1>
              <p className="text-sm text-gray-400 mt-0.5">
                Student ID #{data.student_id}
              </p>
            </div>

            {/* DUS Hero card */}
            <div
              className={`bg-white rounded-2xl border p-6 sm:p-8 flex flex-col sm:flex-row items-center gap-6 shadow-card ${getDusBg(data.overall_dus)}`}
            >
              <DUSGauge score={data.overall_dus} size="lg" />

              <div className="flex flex-col gap-3 flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-gray-900">
                    Durable Understanding Score
                  </h2>
                  <Tooltip text="DUS = 0.30×mastery + 0.30×retention + 0.25×transfer + 0.15×calibration — combines four evidence dimensions into one number." />
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-3xl font-black tabular-nums ${getDusTextClass(data.overall_dus)}`}
                  >
                    {Math.round(data.overall_dus)}
                    <span className="text-lg font-normal text-gray-400">
                      /100
                    </span>
                  </span>
                  <span
                    className={`text-sm font-semibold px-2.5 py-1 rounded-full ${
                      data.overall_dus >= 80
                        ? "bg-green-100 text-green-700"
                        : data.overall_dus >= 60
                          ? "bg-amber-100 text-amber-700"
                          : "bg-red-100 text-red-700"
                    }`}
                  >
                    {getDusLabel(data.overall_dus)} Mastery
                  </span>
                </div>

                <p className="text-sm text-gray-600 leading-relaxed max-w-lg">
                  {data.overall_explanation}
                </p>

                {/* DUS formula */}
                <div className="inline-block bg-gray-900/90 text-gray-200 text-xs font-mono px-3 py-1.5 rounded-lg w-fit mt-1">
                  DUS = 0.30·M + 0.30·R + 0.25·T + 0.15·C
                </div>
              </div>
            </div>

            {/* Four metric cards */}
            {data.topics.length > 0 && (() => {
              // Aggregate across topics for the overview cards
              const avg = (key: keyof typeof data.topics[0]) =>
                Math.round(
                  data.topics.reduce((s, t) => s + (t[key] as number), 0) /
                    data.topics.length,
                );

              const worstTopic = (key: keyof typeof data.topics[0]) =>
                data.topics.reduce((a, b) =>
                  (a[key] as number) < (b[key] as number) ? a : b,
                );

              const retentionTopic = worstTopic("retention");
              const transferTopic = worstTopic("transfer_robustness");
              const calibTopic = worstTopic("calibration");
              const masteryTopic = worstTopic("mastery");

              return (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <MetricCard
                    label="Mastery"
                    score={avg("mastery")}
                    explanation={masteryTopic.mastery_explanation}
                    icon={<BarChart3 className="w-4 h-4" />}
                    sublabel="Recent accuracy on originals"
                  />
                  <MetricCard
                    label="Retention"
                    score={avg("retention")}
                    explanation={retentionTopic.retention_explanation}
                    icon={<Clock className="w-4 h-4" />}
                    sublabel="Accuracy across time gaps"
                  />
                  <MetricCard
                    label="Transfer"
                    score={avg("transfer_robustness")}
                    explanation={transferTopic.transfer_explanation}
                    icon={<Shuffle className="w-4 h-4" />}
                    sublabel="Accuracy on variants vs originals"
                  />
                  <MetricCard
                    label="Calibration"
                    score={avg("calibration")}
                    explanation={calibTopic.calibration_explanation}
                    icon={<Target className="w-4 h-4" />}
                    sublabel={`Confidence accuracy (overconf: ${calibTopic.overconfidence_gap > 0 ? "+" : ""}${Math.round(calibTopic.overconfidence_gap)}pp)`}
                  />
                </div>
              );
            })()}

            {/* Per-topic table */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-gray-700">
                  Per-Topic Breakdown
                </h2>
                <span className="text-xs text-gray-400">
                  {data.topics.length} topic
                  {data.topics.length !== 1 ? "s" : ""}
                </span>
              </div>
              <TopicTable topics={data.topics} studentId={studentId} />
            </section>

            {/* Per-topic detail (collapsible metric cards) */}
            {data.topics.map((topic) => (
              <section key={topic.topic_id} className="animate-fade-in">
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="text-sm font-semibold text-gray-700">
                    {topic.topic_name}
                  </h3>
                  <span className="text-xs text-gray-400">
                    {topic.total_attempts} attempts · DUS{" "}
                    <span
                      className={getDusTextClass(
                        topic.durable_understanding_score,
                      )}
                    >
                      {Math.round(topic.durable_understanding_score)}
                    </span>
                  </span>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <MetricCard
                    label="Mastery"
                    score={topic.mastery}
                    explanation={topic.mastery_explanation}
                    icon={<BarChart3 className="w-4 h-4" />}
                  />
                  <MetricCard
                    label="Retention"
                    score={topic.retention}
                    explanation={topic.retention_explanation}
                    icon={<Clock className="w-4 h-4" />}
                  />
                  <MetricCard
                    label="Transfer"
                    score={topic.transfer_robustness}
                    explanation={topic.transfer_explanation}
                    icon={<Shuffle className="w-4 h-4" />}
                  />
                  <MetricCard
                    label="Calibration"
                    score={topic.calibration}
                    explanation={topic.calibration_explanation}
                    icon={<Target className="w-4 h-4" />}
                    sublabel={
                      topic.overconfidence_gap > 5
                        ? `Overconf: +${Math.round(topic.overconfidence_gap)}pp`
                        : topic.overconfidence_gap < -5
                          ? `Underconf: ${Math.round(topic.overconfidence_gap)}pp`
                          : undefined
                    }
                  />
                </div>
              </section>
            ))}

            {/* Go to tasks CTA */}
            <div className="flex justify-center pt-2 pb-4">
              <Link
                href={`/student/${studentId}/tasks`}
                className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-all hover:scale-[1.02] active:scale-95 shadow-sm"
              >
                <ClipboardList className="w-5 h-5" />
                Go to Tasks
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
