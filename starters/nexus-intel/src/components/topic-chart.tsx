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
import { categoryColors, categoryLabels } from "@/lib/format";

type CategoryItem = {
  category: string;
  item_count: number;
  topic_count: number;
};

export function TopicChart({ data }: { data: CategoryItem[] }) {
  const chartData = data
    .filter((d) => d.item_count > 0)
    .map((d) => ({
      name: categoryLabels[d.category] ?? d.category.replace(/-/g, " "),
      items: d.item_count,
      topics: d.topic_count,
      fill: categoryColors[d.category] ?? "#71717a",
    }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 16, bottom: 4, left: 4 }}
      >
        <XAxis
          type="number"
          tick={{ fontSize: 10, fill: "#a1a1aa" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={150}
          tick={{ fontSize: 10, fill: "#a1a1aa" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#18181b",
            border: "1px solid #27272a",
            borderRadius: "8px",
            fontSize: "12px",
          }}
        />
        <Bar dataKey="items" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
