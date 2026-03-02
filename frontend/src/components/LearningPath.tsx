"use client";

import Link from "next/link";
import { Clock, Shuffle, Target, BarChart3, ArrowRight, CheckCircle2, AlertCircle, TrendingUp } from "lucide-react";
import { cn, getDusTextClass } from "@/lib/utils";
import type { TopicMetrics } from "@/lib/types";

interface LearningPathProps {
  topics: TopicMetrics[];
  studentId: number;
  isFaculty: boolean;
  onTopicClick?: (topic: TopicMetrics) => void;
}

type Tier = "fragile" | "partial" | "durable";

function getTier(dus: number): Tier {
  if (dus >= 80) return "durable";
  if (dus >= 60) return "partial";
  return "fragile";
}

function getWeakestMetric(topic: TopicMetrics): { label: string; score: number; icon: React.ReactNode } {
  const metrics = [
    { label: "Mastery", score: topic.mastery, icon: <BarChart3 className="w-3 h-3" /> },
    { label: "Retention", score: topic.retention, icon: <Clock className="w-3 h-3" /> },
    { label: "Transfer", score: topic.transfer_robustness, icon: <Shuffle className="w-3 h-3" /> },
    { label: "Calibration", score: topic.calibration, icon: <Target className="w-3 h-3" /> },
  ];
  return metrics.reduce((a, b) => (a.score < b.score ? a : b));
}

function getSuggestedAction(topic: TopicMetrics): string {
  const tier = getTier(topic.durable_understanding_score);
  if (tier === "durable") return "Keep practicing to maintain mastery";
  const weak = getWeakestMetric(topic);
  if (weak.label === "Retention") return "Complete scheduled retests to build memory";
  if (weak.label === "Transfer") return "Try transfer exercises with different contexts";
  if (weak.label === "Calibration") return "Work on confidence accuracy — avoid overconfidence";
  return "Practice more questions to boost mastery";
}

const TIER_CONFIG = {
  fragile: {
    label: "Focus Now",
    emoji: "🔴",
    badge: "bg-red-100 text-red-700 border-red-200",
    bar: "bg-red-400",
    ring: "ring-red-200",
    icon: <AlertCircle className="w-4 h-4 text-red-500" />,
    desc: "These topics need immediate attention — DUS below 60",
  },
  partial: {
    label: "Reinforce",
    emoji: "🟡",
    badge: "bg-amber-100 text-amber-700 border-amber-200",
    bar: "bg-amber-400",
    ring: "ring-amber-200",
    icon: <TrendingUp className="w-4 h-4 text-amber-500" />,
    desc: "Getting there — push these above 80 to lock in mastery",
  },
  durable: {
    label: "Mastered",
    emoji: "🟢",
    badge: "bg-green-100 text-green-700 border-green-200",
    bar: "bg-green-400",
    ring: "ring-green-200",
    icon: <CheckCircle2 className="w-4 h-4 text-green-500" />,
    desc: "Durable understanding achieved — well done!",
  },
};

function TopicCard({
  topic,
  studentId,
  isFaculty,
  onClick,
}: {
  topic: TopicMetrics;
  studentId: number;
  isFaculty: boolean;
  onClick?: (topic: TopicMetrics) => void;
}) {
  const tier = getTier(topic.durable_understanding_score);
  const cfg = TIER_CONFIG[tier];
  const weak = getWeakestMetric(topic);
  const action = getSuggestedAction(topic);
  const dus = Math.round(topic.durable_understanding_score);

  return (
    <div
      className={cn("bg-white rounded-xl border shadow-sm p-4 flex flex-col gap-3 ring-1 cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all", cfg.ring)}
      onClick={() => onClick?.(topic)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-gray-800 leading-snug">{topic.topic_name}</p>
          <p className="text-xs text-gray-400 mt-0.5">{topic.total_attempts} attempts</p>
        </div>
        <div className="text-right shrink-0">
          <span className={cn("text-xl font-black tabular-nums", getDusTextClass(topic.durable_understanding_score))}>
            {dus}
          </span>
          <span className="text-xs text-gray-400 ml-0.5">/100</span>
        </div>
      </div>

      {/* DUS progress bar */}
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", cfg.bar)} style={{ width: `${Math.max(2, dus)}%` }} />
      </div>

      {/* Metric mini-scores */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {[
          { label: "M", value: topic.mastery },
          { label: "R", value: topic.retention },
          { label: "T", value: topic.transfer_robustness },
          { label: "C", value: topic.calibration },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 w-3">{label}</span>
            <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full", value >= 80 ? "bg-green-400" : value >= 60 ? "bg-amber-400" : "bg-red-400")}
                style={{ width: `${Math.max(2, value)}%` }}
              />
            </div>
            <span className="text-xs tabular-nums text-gray-500 w-5 text-right">{Math.round(value)}</span>
          </div>
        ))}
      </div>

      {/* Weakest metric tag */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-gray-400">Focus:</span>
        <span className={cn("flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border", cfg.badge)}>
          {weak.icon}
          {weak.label} ({Math.round(weak.score)})
        </span>
      </div>

      {/* Suggested action */}
      <p className="text-xs text-gray-500 leading-snug">{action}</p>

      {/* CTA hint */}
      <p className="text-xs text-indigo-500 font-medium text-center mt-auto">
        Tap to view roadmap →
      </p>
    </div>
  );
}

export default function LearningPath({ topics, studentId, isFaculty, onTopicClick }: LearningPathProps) {
  if (topics.length === 0) return null;

  const sorted = [...topics].sort((a, b) => a.durable_understanding_score - b.durable_understanding_score);

  const tiers: Tier[] = ["fragile", "partial", "durable"];
  const groups = tiers.map((tier) => ({
    tier,
    topics: sorted.filter((t) => getTier(t.durable_understanding_score) === tier),
  })).filter((g) => g.topics.length > 0);

  return (
    <section className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-gray-700">Learning Roadmap</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Topics grouped by mastery level — start from Focus Now
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {groups.map(({ tier, topics: tierTopics }, gi) => {
          const cfg = TIER_CONFIG[tier];
          return (
            <div key={tier}>
              {/* Tier header */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-base">{cfg.emoji}</span>
                <div className="flex items-center gap-2">
                  {cfg.icon}
                  <span className="text-sm font-semibold text-gray-700">{cfg.label}</span>
                  <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full border", cfg.badge)}>
                    {tierTopics.length} topic{tierTopics.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mb-3 ml-7">{cfg.desc}</p>

              {/* Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 ml-0">
                {tierTopics.map((topic) => (
                  <TopicCard
                    key={topic.topic_id}
                    topic={topic}
                    studentId={studentId}
                    isFaculty={isFaculty}
                    onClick={onTopicClick}
                  />
                ))}
              </div>

              {/* Connector arrow between tiers */}
              {gi < groups.length - 1 && (
                <div className="flex justify-center mt-5">
                  <div className="flex flex-col items-center gap-1 text-gray-300">
                    <div className="w-px h-4 bg-gray-200" />
                    <ArrowRight className="w-3.5 h-3.5 rotate-90" />
                    <p className="text-xs text-gray-400">then level up to</p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
