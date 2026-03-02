"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { getDusColor } from "@/lib/utils";
import type { HistogramBucket } from "@/lib/types";

interface DUSHistogramProps {
  data: HistogramBucket[];
}

function bucketMidpoint(label: string): number {
  const parts = label.split("-").map(Number);
  return (parts[0] + parts[1]) / 2;
}

export default function DUSHistogram({ data }: DUSHistogramProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-sm text-slate-500">
        No data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart
        data={data}
        margin={{ top: 4, right: 4, bottom: 4, left: -20 }}
        barCategoryGap="20%"
      >
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "#475569" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#475569" }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.1)",
            background: "#1e1e2e",
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            color: "#f1f5f9",
          }}
          formatter={(value: number, name: string) => {
            if (name === "count") return [`${value} students`, "Count"];
            return [value, name];
          }}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.label}
              fill={getDusColor(bucketMidpoint(entry.label))}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
