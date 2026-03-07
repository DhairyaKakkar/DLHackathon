"use client";

import { useQuery } from "@tanstack/react-query";
import {
  X,
  ExternalLink,
  PlayCircle,
  FileText,
  Code2,
  BookOpen,
  Dumbbell,
  Brain,
  Clock,
  Loader2,
  AlertCircle,
  Target,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { getTopicRoadmap, type TopicRoadmapResource } from "@/lib/api";
import type { TopicMetrics } from "@/lib/types";
import { getDusTextClass, cn } from "@/lib/utils";

interface TopicRoadmapModalProps {
  topic: TopicMetrics;
  studentId: number;
  onClose: () => void;
}

// ─── Resource card ────────────────────────────────────────────────────────────

const RESOURCE_ICONS: Record<string, React.ReactNode> = {
  video:         <PlayCircle className="w-3.5 h-3.5" />,
  article:       <FileText className="w-3.5 h-3.5" />,
  practice:      <Dumbbell className="w-3.5 h-3.5" />,
  course:        <BookOpen className="w-3.5 h-3.5" />,
  documentation: <Code2 className="w-3.5 h-3.5" />,
};

const RESOURCE_COLORS: Record<string, string> = {
  video:         "bg-red-50 text-red-600 border-red-100",
  article:       "bg-blue-50 text-blue-600 border-blue-100",
  practice:      "bg-emerald-50 text-emerald-600 border-emerald-100",
  course:        "bg-purple-50 text-purple-600 border-purple-100",
  documentation: "bg-gray-50 text-gray-600 border-gray-200",
};

function ResourceCard({ res }: { res: TopicRoadmapResource }) {
  const icon  = RESOURCE_ICONS[res.type] ?? <FileText className="w-3.5 h-3.5" />;
  const color = RESOURCE_COLORS[res.type] ?? RESOURCE_COLORS.article;
  return (
    <a
      href={res.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 p-3 bg-white border border-gray-100 rounded-xl hover:border-[#111113] hover:shadow-sm transition-all group"
    >
      <span className={cn("flex items-center justify-center w-7 h-7 rounded-lg border shrink-0 mt-0.5", color)}>
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 group-hover:text-[#e8325a] transition-colors leading-snug">
          {res.title}
        </p>
        <p className="text-xs text-gray-400 mt-0.5 leading-snug">{res.description}</p>
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-gray-300 group-hover:text-[#e8325a] shrink-0 mt-1 transition-colors" />
    </a>
  );
}

// ─── Step node card ───────────────────────────────────────────────────────────

const STEP_COLORS = [
  { border: "border-blue-200 hover:border-blue-400",    dot: "bg-blue-500",    num: "bg-blue-500",    badge: "text-blue-600 bg-blue-50 border-blue-100" },
  { border: "border-violet-200 hover:border-violet-400", dot: "bg-violet-500", num: "bg-violet-500",  badge: "text-violet-600 bg-violet-50 border-violet-100" },
  { border: "border-amber-200 hover:border-amber-400",  dot: "bg-amber-500",   num: "bg-amber-500",   badge: "text-amber-600 bg-amber-50 border-amber-100" },
  { border: "border-emerald-200 hover:border-emerald-400", dot: "bg-emerald-500", num: "bg-emerald-500", badge: "text-emerald-600 bg-emerald-50 border-emerald-100" },
  { border: "border-rose-200 hover:border-rose-400",    dot: "bg-rose-500",    num: "bg-rose-500",    badge: "text-rose-600 bg-rose-50 border-rose-100" },
];

function StepCard({
  number,
  title,
  description,
  duration,
  side,
  isLast,
}: {
  number: number;
  title: string;
  description: string;
  duration: string;
  side: "left" | "right";
  isLast: boolean;
}) {
  const color = STEP_COLORS[(number - 1) % STEP_COLORS.length];

  return (
    <div className={cn("grid items-center gap-0", "grid-cols-[1fr_32px_1fr]")}>
      {/* Left slot */}
      <div className={cn("flex", side === "left" ? "justify-end" : "justify-end opacity-0 pointer-events-none")}>
        {side === "left" && (
          <div className="relative w-full max-w-[280px]">
            {/* Connector line → center */}
            <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full w-4 h-px bg-gray-200" />
            {/* Connector dot at center */}
            <div className={cn(
              "absolute right-0 top-1/2 -translate-y-1/2 translate-x-[calc(100%+16px)] w-2.5 h-2.5 rounded-full ring-2 ring-white",
              color.dot
            )} />
            <StepCardInner number={number} title={title} description={description} duration={duration} color={color} />
          </div>
        )}
      </div>

      {/* Center spine — rendered as empty (the parent provides the line) */}
      <div />

      {/* Right slot */}
      <div className={cn("flex", side === "right" ? "justify-start" : "justify-start opacity-0 pointer-events-none")}>
        {side === "right" && (
          <div className="relative w-full max-w-[280px]">
            {/* Connector line ← center */}
            <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full w-4 h-px bg-gray-200" />
            {/* Connector dot at center */}
            <div className={cn(
              "absolute left-0 top-1/2 -translate-y-1/2 -translate-x-[calc(100%+16px)] w-2.5 h-2.5 rounded-full ring-2 ring-white",
              color.dot
            )} />
            <StepCardInner number={number} title={title} description={description} duration={duration} color={color} />
          </div>
        )}
      </div>
    </div>
  );
}

function StepCardInner({
  number,
  title,
  description,
  duration,
  color,
}: {
  number: number;
  title: string;
  description: string;
  duration: string;
  color: typeof STEP_COLORS[0];
}) {
  return (
    <div className={cn(
      "border-2 rounded-xl bg-white shadow-sm hover:shadow-md transition-all duration-200 px-4 py-3",
      color.border
    )}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className={cn(
            "w-5 h-5 rounded text-white text-[10px] font-bold flex items-center justify-center shrink-0",
            color.num
          )}>
            {number}
          </span>
          <p className="text-sm font-bold text-gray-900 leading-snug">{title}</p>
        </div>
      </div>
      <p className="text-xs text-gray-500 leading-relaxed mb-2">{description}</p>
      {duration && (
        <span className={cn("inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border", color.badge)}>
          <Clock className="w-2.5 h-2.5" />
          {duration}
        </span>
      )}
    </div>
  );
}

// ─── Section label on the center line ────────────────────────────────────────

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex justify-center my-2">
      <div className="relative bg-[#fafaf8] px-4">
        <div className="absolute left-1/2 -translate-x-1/2 -top-4 w-px h-4 bg-gray-200" />
        <span className="inline-flex items-center gap-2 px-4 py-1.5 bg-white border-2 border-gray-100 rounded-lg text-xs font-bold text-gray-600 uppercase tracking-wide shadow-sm">
          {label}
        </span>
      </div>
    </div>
  );
}

// ─── Main modal ───────────────────────────────────────────────────────────────

export default function TopicRoadmapModal({ topic, studentId, onClose }: TopicRoadmapModalProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["topicRoadmap", studentId, topic.topic_id],
    queryFn: () => getTopicRoadmap(studentId, topic.topic_id),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const dus = Math.round(topic.durable_understanding_score);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative bg-[#fafaf8] w-full sm:max-w-2xl sm:rounded-2xl rounded-t-2xl shadow-2xl max-h-[92vh] flex flex-col overflow-hidden border border-gray-200">

        {/* ── Header ── */}
        <div className="bg-white border-b border-gray-100 px-5 py-4 flex items-start justify-between gap-3 shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Brain className="w-4 h-4 text-[#e8325a]" />
              <h2 className="text-base font-bold text-gray-900">{topic.topic_name}</h2>
            </div>
            <p className="text-xs text-gray-400">
              DUS{" "}
              <span className={cn("font-bold", getDusTextClass(topic.durable_understanding_score))}>
                {dus}
              </span>
              /100 · {topic.total_attempts} attempts
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Content ── */}
        <div className="overflow-y-auto flex-1 px-5 py-5 flex flex-col gap-5">

          {/* Loading */}
          {isLoading && (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Loader2 className="w-8 h-8 text-[#e8325a] animate-spin" />
              <p className="text-sm font-semibold text-gray-700">Generating your personalised roadmap…</p>
              <p className="text-xs text-gray-400">GPT-4o is analysing your metrics and curating resources</p>
            </div>
          )}

          {/* Error */}
          {isError && (
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <AlertCircle className="w-8 h-8 text-red-400" />
              <p className="text-sm font-semibold text-gray-700">Roadmap generation failed</p>
              <p className="text-xs text-gray-400">Make sure OPENAI_API_KEY is set in docker-compose.yml</p>
            </div>
          )}

          {/* Loaded */}
          {data && (
            <>
              {/* Diagnosis */}
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3">
                <Target className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">
                    What's holding you back
                  </p>
                  <p className="text-sm text-amber-900 leading-relaxed">{data.diagnosis}</p>
                </div>
              </div>

              {/* Key concepts */}
              <div>
                <div className="flex items-center gap-2 mb-2.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#e8325a]" />
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Key concepts to focus on</p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {data.concepts.map((c) => (
                    <span
                      key={c}
                      className="text-xs font-medium bg-[#fff0f3] text-[#e8325a] border border-[#fecdd3] px-2.5 py-1 rounded-lg"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              {/* ── Timeline Study Plan ── */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-3.5 h-3.5 text-gray-400" />
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Study plan</p>
                  </div>
                  <span className="flex items-center gap-1 text-xs text-gray-400 bg-gray-100 px-2.5 py-1 rounded-lg">
                    <Clock className="w-3 h-3" />
                    ~{data.estimated_weeks} week{data.estimated_weeks !== 1 ? "s" : ""} to DUS 80
                  </span>
                </div>

                {/* Timeline container */}
                <div className="relative px-2">
                  {/* Central vertical line */}
                  <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-px bg-gray-200 z-0" />

                  {/* Section label at top */}
                  <SectionLabel label="Start here" />

                  {/* Steps */}
                  <div className="relative z-10 flex flex-col gap-5 mt-4">
                    {data.steps.map((step, i) => (
                      <StepCard
                        key={step.number}
                        number={step.number}
                        title={step.title}
                        description={step.description}
                        duration={step.duration}
                        side={i % 2 === 0 ? "left" : "right"}
                        isLast={i === data.steps.length - 1}
                      />
                    ))}
                  </div>

                  {/* Section label at bottom */}
                  <div className="mt-4">
                    <SectionLabel label="DUS 80+ goal" />
                  </div>
                  {/* End dot */}
                  <div className="flex justify-center mt-2">
                    <div className="w-4 h-4 rounded-full bg-emerald-500 ring-4 ring-emerald-100 flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-white" />
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Resources ── */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <BookOpen className="w-3.5 h-3.5 text-gray-400" />
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Curated resources</p>
                </div>
                <div className="flex flex-col gap-2">
                  {data.resources.map((res) => (
                    <ResourceCard key={res.url + res.title} res={res} />
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
