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
import { platformColors } from "@/lib/format";

type EngagementItem = {
  author_name: string | null;
  platform: string;
  total_likes: number;
  avg_likes: number;
  post_count: number;
};

export function EngagementChart({ data }: { data: EngagementItem[] }) {
  const chartData = data
    .filter((d) => d.total_likes > 0)
    .slice(0, 10)
    .map((d) => ({
      name: d.author_name?.split(" ")[0] ?? "?",
      fullName: d.author_name,
      likes: d.total_likes,
      avg: Math.round(d.avg_likes),
      posts: d.post_count,
      platform: d.platform,
    }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: "#a1a1aa" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#a1a1aa" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) =>
            v >= 1000 ? `${(v / 1000).toFixed(0)}K` : String(v)
          }
        />
        <Tooltip
          contentStyle={{
            background: "#18181b",
            border: "1px solid #27272a",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any, _name: any, props: any) => [
            `${Number(value).toLocaleString()} total (avg ${props?.payload?.avg ?? 0}, ${props?.payload?.posts ?? 0} posts)`,
            props?.payload?.fullName ?? "",
          ]}
        />
        <Bar dataKey="likes" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={platformColors[entry.platform] ?? "#71717a"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
