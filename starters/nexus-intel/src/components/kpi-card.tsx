"use client";

import { Card, CardContent } from "@/components/ui/card";
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { AnimateCount } from "@/components/unlumen/animate-count";
import { formatNum } from "@/lib/format";

type KpiCardProps = {
  label: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  sparkline?: number[];
  accent?: "emerald" | "blue" | "amber" | "purple" | "red" | "cyan" | "rose";
};

const accentColors: Record<NonNullable<KpiCardProps["accent"]>, string> = {
  emerald: "#10b981",
  blue: "#3b82f6",
  amber: "#f59e0b",
  purple: "#a855f7",
  red: "#ef4444",
  cyan: "#06b6d4",
  rose: "#f43f5e",
};

export function KpiCard({
  label,
  value,
  delta,
  deltaLabel = "WoW",
  sparkline,
  accent = "emerald",
}: KpiCardProps) {
  const hasDelta = typeof delta === "number";
  const trendUp = hasDelta && delta! > 0;
  const trendDown = hasDelta && delta! < 0;
  const flat = hasDelta && delta === 0;
  const color = accentColors[accent];

  const sparkData =
    sparkline && sparkline.length > 0 ? sparkline.map((v, i) => ({ i, v })) : null;

  return (
    <Card className="relative overflow-hidden hover:border-primary/30 transition-colors">
      {sparkData && (
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`spark-${accent}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.6} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#spark-${accent})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
      <CardContent className="pt-4 pb-3 px-4 relative">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <p className="text-2xl font-bold mt-1">
          {typeof value === "number" ? (
            <AnimateCount to={value} format={formatNum} />
          ) : (
            value
          )}
        </p>
        {hasDelta && (
          <div className="flex items-center gap-1 mt-1">
            {trendUp && <ArrowUpIcon className="size-3 text-emerald-500" />}
            {trendDown && <ArrowDownIcon className="size-3 text-rose-500" />}
            {flat && <MinusIcon className="size-3 text-muted-foreground" />}
            <span
              className={`text-[10px] font-medium ${
                trendUp
                  ? "text-emerald-500"
                  : trendDown
                    ? "text-rose-500"
                    : "text-muted-foreground"
              }`}
            >
              {trendUp ? "+" : ""}
              {delta}
            </span>
            <span className="text-[10px] text-muted-foreground">{deltaLabel}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
