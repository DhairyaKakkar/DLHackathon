"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Clock,
  Shuffle,
  Target,
  BarChart3,
  ClipboardList,
  Info,
  LogOut,
  GraduationCap,
  Calendar,
} from "lucide-react";
import { getStudentDashboard, getStudentSchedule } from "@/lib/api";
import { getAuth, clearAuth, type EaleAuth } from "@/lib/auth";
import {
  getDusTextClass,
  getDusBg,
  getDusLabel,
} from "@/lib/utils";
import type { TopicMetrics, ClassScheduleOut } from "@/lib/types";
import DUSGauge from "@/components/DUSGauge";
import MetricCard from "@/components/MetricCard";
import TopicTable from "@/components/TopicTable";
import LearningPath from "@/components/LearningPath";
import TopicRoadmapModal from "@/components/TopicRoadmapModal";
import ScheduleOnboardingModal from "@/components/ScheduleOnboardingModal";
import PreClassAlert from "@/components/PreClassAlert";
import CameraConsentModal, { CameraIndicator } from "@/components/CameraConsentModal";
import { StudentDashboardSkeleton } from "@/components/Skeletons";
import ErrorState from "@/components/ErrorState";
import Navbar from "@/components/Navbar";

function Tooltip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <Info className="w-3.5 h-3.5 text-[#9e9eae] hover:text-[#5c5c6e] cursor-help transition-colors" />
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-52 bg-[#111113] text-white text-xs rounded-lg px-2.5 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity leading-snug z-30 shadow-xl">
        {text}
      </span>
    </span>
  );
}

export default function StudentDashboardPage() {
  const params = useParams();
  const router = useRouter();
  const studentId = Number(params.id);
  const [auth, setAuthState] = useState<EaleAuth | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<"overview" | "roadmap">("overview");
  const [selectedTopic, setSelectedTopic] = useState<TopicMetrics | null>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showCameraConsent, setShowCameraConsent] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [scheduleLoaded, setScheduleLoaded] = useState(false);

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

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["studentDashboard", studentId],
    queryFn: () => getStudentDashboard(studentId),
    enabled: !isNaN(studentId) && !checking,
  });

  const { data: schedules = [] } = useQuery<ClassScheduleOut[]>({
    queryKey: ["schedule", studentId],
    queryFn: () => getStudentSchedule(studentId),
    enabled: !isNaN(studentId) && !checking && auth?.role === "student",
    onSuccess: (data) => {
      // Show onboarding if student has no schedule yet
      if (!scheduleLoaded) {
        setScheduleLoaded(true);
        if (data.length === 0) setShowScheduleModal(true);
      }
    },
  } as any);

  // Camera consent — check localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const consent = localStorage.getItem("eale_camera_consent");
      if (consent === "accepted") setCameraActive(true);
    }
  }, []);

  const urgentClasses = schedules.filter((s: ClassScheduleOut) => s.is_urgent || s.is_upcoming);

  function handleSignOut() {
    clearAuth();
    router.replace("/login");
  }

  if (checking) return null;

  const isFaculty = auth?.role === "faculty";
  const backHref = isFaculty ? "/faculty" : undefined;
  const backLabel = isFaculty ? "← Cohort" : undefined;

  return (
    <div className="min-h-screen bg-[#fafaf8]">
      <Navbar
        backHref={backHref}
        backLabel={backLabel}
        title={data?.student_name}
        action={
          <div className="flex items-center gap-2">
            {!isFaculty && (
              <>
                <button
                  onClick={() => setShowScheduleModal(true)}
                  className="flex items-center gap-1.5 text-sm text-[#9e9eae] hover:text-[#111113] transition-colors px-2 py-2 rounded-lg hover:bg-black/[0.04]"
                  title="Manage schedule"
                >
                  <Calendar className="w-4 h-4" />
                </button>
                <CameraIndicator
                  active={cameraActive}
                  onToggle={() => {
                    if (!cameraActive) {
                      setShowCameraConsent(true);
                    } else {
                      setCameraActive(false);
                      localStorage.setItem("eale_camera_consent", "declined");
                    }
                  }}
                />
                <Link
                  href={`/student/${studentId}/tasks`}
                  className="flex items-center gap-1.5 bg-[#111113] text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#2a2a32] transition-colors"
                >
                  <ClipboardList className="w-4 h-4" />
                  Tasks
                </Link>
              </>
            )}
            {isFaculty && (
              <span className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg font-semibold">
                <GraduationCap className="w-3.5 h-3.5" />
                Faculty view
              </span>
            )}
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

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {isLoading && <StudentDashboardSkeleton />}

        {isError && (
          <ErrorState message={(error as Error)?.message} onRetry={() => refetch()} />
        )}

        {/* Pre-class alert */}
        {!isFaculty && urgentClasses.length > 0 && (
          <div className="mb-2">
            <PreClassAlert urgentClasses={urgentClasses} studentId={studentId} />
          </div>
        )}

        {data && (
          <div className="flex flex-col gap-6 animate-fade-in">
            {/* Page header */}
            <div>
              <h1 className="font-display italic text-2xl font-bold text-[#111113]">
                {data.student_name}
              </h1>
              <p className="text-sm text-[#9e9eae] mt-0.5 font-mono">
                Student #{data.student_id}
              </p>
            </div>

            {/* DUS Hero card */}
            <div className={`rounded-xl border p-6 sm:p-8 flex flex-col sm:flex-row items-center gap-6 shadow-card ${getDusBg(data.overall_dus)}`}>
              <DUSGauge score={data.overall_dus} size="lg" />

              <div className="flex flex-col gap-3 flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-[#111113]">
                    Durable Understanding Score
                  </h2>
                  <Tooltip text="DUS = 0.30×mastery + 0.30×retention + 0.25×transfer + 0.15×calibration — combines four evidence dimensions into one number." />
                </div>

                <div className="flex items-center gap-3">
                  <span className={`text-3xl font-bold tabular-nums font-mono ${getDusTextClass(data.overall_dus)}`}>
                    {Math.round(data.overall_dus)}
                    <span className="text-lg font-normal text-[#9e9eae]">/100</span>
                  </span>
                  <span className={`text-sm font-semibold px-2.5 py-1 rounded border ${
                    data.overall_dus >= 80
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : data.overall_dus >= 60
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-red-50 text-red-600 border-red-200"
                  }`}>
                    {getDusLabel(data.overall_dus)} Mastery
                  </span>
                </div>

                <p className="text-sm text-[#5c5c6e] leading-relaxed max-w-lg">
                  {data.overall_explanation}
                </p>

                <div className="inline-block bg-white border border-[#d0cec9] text-[#5c5c6e] text-xs font-mono px-3 py-1.5 rounded w-fit mt-1">
                  DUS = 0.30·M + 0.30·R + 0.25·T + 0.15·C
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-0 border border-[#d0cec9] rounded-lg w-fit overflow-hidden">
              {(["overview", "roadmap"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-5 py-2 text-sm font-semibold transition-all capitalize ${
                    tab === t
                      ? "bg-[#111113] text-white"
                      : "bg-white text-[#5c5c6e] hover:text-[#111113] hover:bg-[#fafaf8]"
                  }`}
                >
                  {t === "roadmap" ? "Roadmap" : "Overview"}
                </button>
              ))}
            </div>

            {/* Overview tab */}
            {tab === "overview" && (
              <>
                {data.topics.length > 0 && (() => {
                  const avg = (key: keyof typeof data.topics[0]) =>
                    Math.round(data.topics.reduce((s, t) => s + (t[key] as number), 0) / data.topics.length);
                  const worstTopic = (key: keyof typeof data.topics[0]) =>
                    data.topics.reduce((a, b) => (a[key] as number) < (b[key] as number) ? a : b);
                  const retentionTopic = worstTopic("retention");
                  const transferTopic = worstTopic("transfer_robustness");
                  const calibTopic = worstTopic("calibration");
                  const masteryTopic = worstTopic("mastery");

                  return (
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      <MetricCard label="Mastery" score={avg("mastery")} explanation={masteryTopic.mastery_explanation} icon={<BarChart3 className="w-4 h-4" />} sublabel="Recent accuracy on originals" />
                      <MetricCard label="Retention" score={avg("retention")} explanation={retentionTopic.retention_explanation} icon={<Clock className="w-4 h-4" />} sublabel="Accuracy across time gaps" />
                      <MetricCard label="Transfer" score={avg("transfer_robustness")} explanation={transferTopic.transfer_explanation} icon={<Shuffle className="w-4 h-4" />} sublabel="Accuracy on variants vs originals" />
                      <MetricCard label="Calibration" score={avg("calibration")} explanation={calibTopic.calibration_explanation} icon={<Target className="w-4 h-4" />} sublabel={`Confidence accuracy (overconf: ${calibTopic.overconfidence_gap > 0 ? "+" : ""}${Math.round(calibTopic.overconfidence_gap)}pp)`} />
                    </div>
                  );
                })()}

                <section>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-[#5c5c6e] uppercase tracking-widest">Per-Topic Breakdown</h2>
                    <span className="text-xs text-[#9e9eae] font-mono">{data.topics.length} topic{data.topics.length !== 1 ? "s" : ""}</span>
                  </div>
                  <TopicTable topics={data.topics} studentId={studentId} />
                </section>

                {!isFaculty && (
                  <div className="flex justify-center pt-2 pb-4">
                    <Link
                      href={`/student/${studentId}/tasks`}
                      className="flex items-center gap-2 bg-[#111113] text-white px-6 py-3 rounded-xl font-semibold hover:bg-[#2a2a32] transition-all hover:scale-[1.02] active:scale-95"
                    >
                      <ClipboardList className="w-5 h-5" />
                      Go to Tasks
                    </Link>
                  </div>
                )}
              </>
            )}

            {/* Roadmap tab */}
            {tab === "roadmap" && (
              <LearningPath
                topics={data.topics}
                studentId={studentId}
                isFaculty={isFaculty}
                onTopicClick={setSelectedTopic}
                schedules={schedules}
              />
            )}
          </div>
        )}

        {selectedTopic && (
          <TopicRoadmapModal
            topic={selectedTopic}
            studentId={studentId}
            onClose={() => setSelectedTopic(null)}
          />
        )}

        {showScheduleModal && !isFaculty && (
          <ScheduleOnboardingModal
            studentId={studentId}
            onComplete={() => setShowScheduleModal(false)}
          />
        )}

        {showCameraConsent && (
          <CameraConsentModal
            onAccept={() => {
              setCameraActive(true);
              localStorage.setItem("eale_camera_consent", "accepted");
              setShowCameraConsent(false);
            }}
            onDecline={() => {
              setCameraActive(false);
              localStorage.setItem("eale_camera_consent", "declined");
              setShowCameraConsent(false);
            }}
          />
        )}
      </main>
    </div>
  );
}
