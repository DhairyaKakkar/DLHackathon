"use client";

import { getDusColor, getDusLabel } from "@/lib/utils";

interface DUSGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

export default function DUSGauge({ score, size = "lg" }: DUSGaugeProps) {
  const RADIUS = 80;
  const STROKE = 14;
  const CENTER_X = 110;
  const CENTER_Y = 108;

  // The half-circle path: from left to right, through the top
  // M (centerX - radius, centerY) A radius radius 0 0 1 (centerX + radius, centerY)
  const startX = CENTER_X - RADIUS;
  const endX = CENTER_X + RADIUS;
  const arcPath = `M ${startX} ${CENTER_Y} A ${RADIUS} ${RADIUS} 0 0 1 ${endX} ${CENTER_Y}`;

  // Total arc length = π × r
  const arcLen = Math.PI * RADIUS;
  const progress = Math.max(0, Math.min(100, score));
  const dashOffset = arcLen * (1 - progress / 100);

  const color = getDusColor(score);
  const label = getDusLabel(score);

  const dimensions =
    size === "sm"
      ? { w: 160, h: 95, scale: 0.73 }
      : size === "md"
        ? { w: 190, h: 115, scale: 0.87 }
        : { w: 220, h: 130, scale: 1 };

  const textSizes =
    size === "sm"
      ? { score: "2rem", label: "0.65rem" }
      : size === "md"
        ? { score: "2.4rem", label: "0.75rem" }
        : { score: "2.8rem", label: "0.85rem" };

  return (
    <div
      className="flex flex-col items-center"
      style={{ width: dimensions.w }}
    >
      <svg
        viewBox="0 0 220 130"
        width={dimensions.w}
        height={dimensions.h}
        aria-label={`Durable Understanding Score: ${score}`}
      >
        {/* Track */}
        <path
          d={arcPath}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={STROKE}
          strokeLinecap="round"
        />

        {/* Progress arc */}
        <path
          d={arcPath}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${arcLen} ${arcLen}`}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.8s ease-out", filter: `drop-shadow(0 0 6px ${color}60)` }}
        />

        {/* Score number */}
        <text
          x={CENTER_X}
          y={CENTER_Y - 10}
          textAnchor="middle"
          dominantBaseline="middle"
          fontWeight="800"
          fontSize={textSizes.score}
          fill={color}
          fontFamily="Inter, system-ui, sans-serif"
        >
          {Math.round(score)}
        </text>

        {/* Label */}
        <text
          x={CENTER_X}
          y={CENTER_Y + 16}
          textAnchor="middle"
          dominantBaseline="middle"
          fontWeight="600"
          fontSize={textSizes.label}
          fill="#475569"
          letterSpacing="0.08em"
          fontFamily="Inter, system-ui, sans-serif"
        >
          {label.toUpperCase()}
        </text>

        {/* Range labels */}
        <text
          x={startX - 2}
          y={CENTER_Y + 18}
          textAnchor="middle"
          fontSize="0.6rem"
          fill="#334155"
          fontFamily="Inter, system-ui, sans-serif"
        >
          0
        </text>
        <text
          x={endX + 2}
          y={CENTER_Y + 18}
          textAnchor="middle"
          fontSize="0.6rem"
          fill="#334155"
          fontFamily="Inter, system-ui, sans-serif"
        >
          100
        </text>
      </svg>
    </div>
  );
}
