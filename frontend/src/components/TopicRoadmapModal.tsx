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
  ChevronRight,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { getTopicRoadmap, type TopicRoadmapResource } from "@/lib/api";
import type { TopicMetrics } from "@/lib/types";
import { getDusTextClass, cn } from "@/lib/utils";

interface TopicRoadmapModalProps {
  topic: TopicMetrics;
  studentId: number;
  onClose: () => void;
}

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
  practice:      "bg-green-50 text-green-600 border-green-100",
  course:        "bg-purple-50 text-purple-600 border-purple-100",
  documentation: "bg-gray-50 text-gray-600 border-gray-200",
};

function ResourceCard({ res }: { res: TopicRoadmapResource }) {
  const icon = RESOURCE_ICONS[res.type] ?? <FileText className="w-3.5 h-3.5" />;
  const color = RESOURCE_COLORS[res.type] ?? RESOURCE_COLORS.article;

  return (
    <a
      href={res.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 p-3 bg-white border border-[#d0cec9] rounded-lg hover:border-[#111113] transition-all group"
    >
      <span className={cn("flex items-center justify-center w-7 h-7 rounded-lg border shrink-0 mt-0.5", color)}>
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[#111113] group-hover:text-[#e8325a] transition-colors leading-snug">
          {res.title}
        </p>
        <p className="text-xs text-gray-400 mt-0.5 leading-snug">{res.description}</p>
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-[#9e9eae] group-hover:text-[#e8325a] shrink-0 mt-1 transition-colors" />
    </a>
  );
}

export default function TopicRoadmapModal({ topic, studentId, onClose }: TopicRoadmapModalProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["topicRoadmap", studentId, topic.topic_id],
    queryFn: () => getTopicRoadmap(studentId, topic.topic_id),
    staleTime: 10 * 60 * 1000,   // cache for 10 min — GPT-4o is slow+expensive
    retry: 1,
  });

  const dus = Math.round(topic.durable_understanding_score);

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Panel */}
      <div className="relative bg-[#fafaf8] w-full sm:max-w-2xl sm:rounded-xl rounded-t-xl shadow-panel max-h-[92vh] flex flex-col overflow-hidden border border-[#d0cec9]">
        {/* Header */}
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

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-5 flex flex-col gap-5">

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
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
                <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1.5">
                  What's holding you back
                </p>
                <p className="text-sm text-amber-900 leading-relaxed">{data.diagnosis}</p>
              </div>

              {/* Key concepts */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Key concepts to focus on
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {data.concepts.map((c) => (
                    <span
                      key={c}
                      className="text-xs font-medium bg-[#fff0f3] text-[#e8325a] border border-[#fecdd3] px-2.5 py-1 rounded"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              {/* Study plan */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Study plan
                  </p>
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <Clock className="w-3 h-3" />
                    ~{data.estimated_weeks} week{data.estimated_weeks !== 1 ? "s" : ""} to DUS 80
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {data.steps.map((step, i) => (
                    <div key={step.number} className="flex gap-3">
                      <div className="flex flex-col items-center gap-1 shrink-0">
                        <div className="w-6 h-6 rounded bg-[#111113] text-white flex items-center justify-center text-xs font-bold font-mono">
                          {step.number}
                        </div>
                        {i < data.steps.length - 1 && (
                          <div className="w-px flex-1 bg-[#ece9e4] min-h-[16px]" />
                        )}
                      </div>
                      <div className="pb-3 flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className="text-sm font-semibold text-gray-800">{step.title}</p>
                          <span className="text-xs text-gray-400 shrink-0">{step.duration}</span>
                        </div>
                        <p className="text-xs text-gray-500 leading-relaxed">{step.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Resources */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Curated resources
                </p>
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
