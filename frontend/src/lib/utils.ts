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
  if (level === "durable") return "#22c55e";
  if (level === "partial") return "#f59e0b";
  return "#ef4444";
}

export function getDusBg(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable") return "bg-green-50 border-green-200";
  if (level === "partial") return "bg-amber-50 border-amber-200";
  return "bg-red-50 border-red-200";
}

export function getDusTextClass(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable") return "text-green-600";
  if (level === "partial") return "text-amber-600";
  return "text-red-600";
}

export function getDusBadgeClass(score: number): string {
  const level = getDusLevel(score);
  if (level === "durable")
    return "bg-green-100 text-green-700 border border-green-200";
  if (level === "partial")
    return "bg-amber-100 text-amber-700 border border-amber-200";
  return "bg-red-100 text-red-700 border border-red-200";
}

export function getMetricColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export function getMetricBarColor(score: number): string {
  if (score >= 80) return "bg-green-500";
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
