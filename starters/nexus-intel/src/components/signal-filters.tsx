"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

const URGENCY_OPTIONS = [
  { id: "all", label: "All" },
  { id: "act-now", label: "Act Now" },
  { id: "this-week", label: "This Week" },
  { id: "this-month", label: "This Month" },
];

const TYPE_OPTIONS = [
  { id: "all", label: "All Types" },
  { id: "content-angle", label: "Content" },
  { id: "engagement-hook", label: "Engagement" },
  { id: "audience-pain-point", label: "Pain Point" },
  { id: "trend", label: "Trend" },
  { id: "vulnerability", label: "Gap" },
];

export function SignalFilters({
  activeUrgency,
  activeType,
}: {
  activeUrgency: string;
  activeType: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function setFilter(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "all") {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    router.push(`/signals?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* Urgency filters */}
      <div className="relative flex items-center gap-0.5 rounded-full bg-secondary/50 p-1">
        {URGENCY_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setFilter("urgency", opt.id)}
            className={cn(
              "relative z-10 rounded-full px-3 py-1 text-xs font-medium transition-colors",
              activeUrgency === opt.id
                ? "text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {activeUrgency === opt.id && (
              <motion.div
                layoutId="urgency-pill"
                className="absolute inset-0 rounded-full bg-primary"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        ))}
      </div>

      {/* Type filters */}
      <div className="relative flex items-center gap-0.5 rounded-full bg-secondary/50 p-1">
        {TYPE_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setFilter("type", opt.id)}
            className={cn(
              "relative z-10 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              activeType === opt.id
                ? "text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {activeType === opt.id && (
              <motion.div
                layoutId="type-pill"
                className="absolute inset-0 rounded-full bg-accent"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
