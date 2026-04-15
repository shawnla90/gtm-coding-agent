"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { platformColors, platformLabels } from "@/lib/format";

export function PlatformChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([platform, count]) => ({
    name: platformLabels[platform] ?? platform,
    value: count,
    fill: platformColors[platform] ?? "#71717a",
  }));

  return (
    <div className="flex items-center gap-6">
      <ResponsiveContainer width="50%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            strokeWidth={2}
            stroke="#18181b"
          >
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#18181b",
              border: "1px solid #27272a",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-3">
        {chartData.map((entry) => (
          <div key={entry.name} className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: entry.fill }}
            />
            <div>
              <p className="text-xs font-medium">{entry.name}</p>
              <p className="text-[10px] text-muted-foreground">
                {entry.value.toLocaleString()} posts
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
