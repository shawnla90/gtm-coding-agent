"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

type TrendPoint = {
  week_start: string;
  likes: number;
  comments: number;
  posts: number;
};

export function MomentumChart({ data }: { data: TrendPoint[] }) {
  const chartData = data.map((d) => ({
    week: new Date(d.week_start).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    likes: d.likes,
    comments: d.comments,
    posts: d.posts,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <defs>
          <linearGradient id="momentumGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
        <XAxis
          dataKey="week"
          tick={{ fontSize: 10, fill: "#a1a1aa" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#a1a1aa" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) =>
            v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
          }
        />
        <Tooltip
          contentStyle={{
            background: "#09090b",
            border: "1px solid #27272a",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelStyle={{ color: "#a1a1aa", fontSize: "11px" }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any, name: any) => [
            Number(value).toLocaleString(),
            typeof name === "string"
              ? name.charAt(0).toUpperCase() + name.slice(1)
              : String(name),
          ]}
        />
        <Area
          type="monotone"
          dataKey="likes"
          stroke="#10b981"
          strokeWidth={2}
          fill="url(#momentumGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
