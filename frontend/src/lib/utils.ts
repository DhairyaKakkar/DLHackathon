import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type DusLevel = "durable" | "partial" | "fragile";

export function getDusLevel(score: number): DusLevel {
  if (score >= 80) return "durable";
  if (score >= 60) return "partial";
  return "fragile";
}

export function getDusLabel(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable") return "Durable";
  if (level === "partial") return "Partial";
  return "Fragile";
}

export function getDusColor(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable") return "#10b981";
  if (level === "partial") return "#f59e0b";
  return "#f43f5e";
}

export function getDusBg(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable") return "bg-emerald-500/10 border-emerald-500/30";
  if (level === "partial") return "bg-amber-500/10 border-amber-500/30";
  return "bg-red-500/10 border-red-500/30";
}

export function getDusTextClass(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable") return "text-emerald-400";
  if (level === "partial") return "text-amber-400";
  return "text-red-400";
}

export function getDusBadgeClass(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable")
    return "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
  if (level === "partial")
    return "bg-amber-500/15 text-amber-400 border border-amber-500/30";
  return "bg-red-500/15 text-red-400 border border-red-500/30";
}

export function getMetricColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

export function getMetricBarColor(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-500";
}

/** Pick the most alarming metric as the "top risk" reason for a topic. */
export function getTopRisk(topic: {
  retention: number;
  transfer_robustness: number;
  calibration: number;
  overconfidence_gap: number;
}): string {
  const issues: Array<[number, string]> = [
    [topic.transfer_robustness, "Poor transfer"],
    [topic.retention, "Low retention"],
    [topic.calibration, "Calibration issues"],
  ];
  // Overconfidence is special — flag it if gap > 15pp
  if (topic.overconfidence_gap > 15) {
    return `Overconfident (+${Math.round(topic.overconfidence_gap)}pp)`;
  }
  const worst = issues.sort((a, b) => a[0] - b[0])[0];
  return worst[1];
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMins = Math.floor(diffMs / (1000 * 60));

  if (diffMs < 0) {
    const futureDays = Math.ceil(-diffMs / (1000 * 60 * 60 * 24));
    if (futureDays === 1) return "due tomorrow";
    return `due in ${futureDays}d`;
  }
  if (diffMins < 60) return diffMins <= 1 ? "just now" : `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "yesterday";
  return `${diffDays}d ago`;
}

export function formatTaskType(type: "RETEST" | "TRANSFER"): string {
  return type === "RETEST" ? "Retest" : "Transfer";
}
