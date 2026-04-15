"use client";

import { useState, useEffect, useCallback } from "react";
import { RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { signalTypeLabels } from "@/lib/format";

const STORAGE_KEY = "apollo-signal-weights";

// Signal type colors for the meter bars (hex for inline styles)
const METER_COLORS: Record<string, string> = {
  "content-angle": "#F59E0B",
  "engagement-hook": "#3B82F6",
  "audience-pain-point": "#F43F5E",
  positioning: "#A855F7",
  vulnerability: "#EF4444",
  trend: "#D4A843",
  "product-launch": "#10B981",
  opportunity: "#06B6D4",
  "content-gap": "#6366F1",
  partnership: "#F97316",
};

interface Props {
  typeCounts: { signal_type: string; count: number }[];
  onWeightsChange: (weights: Record<string, number>) => void;
}

function loadWeights(): Record<string, number> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveWeights(w: Record<string, number>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(w));
}

export function SignalMeter({ typeCounts, onWeightsChange }: Props) {
  const [weights, setWeights] = useState<Record<string, number>>({});

  // Load from localStorage on mount
  useEffect(() => {
    setWeights(loadWeights());
  }, []);

  const totalSignals = typeCounts.reduce((s, t) => s + t.count, 0);

  const getWeight = (type: string) => weights[type] ?? 1;

  const handleWeight = useCallback(
    (type: string, value: number) => {
      const next = { ...weights, [type]: value };
      setWeights(next);
      saveWeights(next);
      onWeightsChange(next);
    },
    [weights, onWeightsChange],
  );

  const handleReset = useCallback(() => {
    const empty: Record<string, number> = {};
    setWeights(empty);
    saveWeights(empty);
    onWeightsChange(empty);
  }, [onWeightsChange]);

  return (
    <div className="space-y-5 p-4">
      {/* Visual gauge — stacked bar */}
      <div>
        <h4 className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Signal Distribution
        </h4>
        {totalSignals > 0 ? (
          <div className="flex h-5 w-full overflow-hidden rounded-full bg-secondary/30">
            {typeCounts.map((tc) => {
              const pct = (tc.count / totalSignals) * 100;
              if (pct < 1) return null;
              return (
                <div
                  key={tc.signal_type}
                  className="relative flex items-center justify-center transition-all duration-300"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: METER_COLORS[tc.signal_type] ?? "#6B7280",
                  }}
                  title={`${signalTypeLabels[tc.signal_type] ?? tc.signal_type}: ${tc.count}`}
                >
                  {pct > 8 && (
                    <span className="text-[8px] font-bold text-white/90 truncate px-0.5">
                      {tc.count}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="h-5 w-full rounded-full bg-secondary/30" />
        )}
        <p className="mt-1 text-[10px] text-muted-foreground">
          {totalSignals} signals across {typeCounts.length} types
        </p>
      </div>

      {/* Config panel — weight sliders */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Weight Configuration
          </h4>
          <button
            onClick={handleReset}
            className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
          >
            <RotateCcw className="h-2.5 w-2.5" />
            Reset
          </button>
        </div>
        <div className="space-y-3">
          {typeCounts.map((tc) => {
            const w = getWeight(tc.signal_type);
            const label = signalTypeLabels[tc.signal_type] ?? tc.signal_type;
            const color = METER_COLORS[tc.signal_type] ?? "#6B7280";
            return (
              <div key={tc.signal_type} className="space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs text-foreground/80">{label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground tabular-nums">
                      {tc.count}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] font-bold tabular-nums min-w-[2ch] text-right",
                        w === 0 ? "text-muted-foreground/50" :
                        w >= 2 ? "text-primary" : "text-foreground/70",
                      )}
                    >
                      {w}x
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min={0}
                  max={3}
                  step={1}
                  value={w}
                  onChange={(e) =>
                    handleWeight(tc.signal_type, Number(e.target.value))
                  }
                  className="w-full h-1.5 rounded-full appearance-none cursor-pointer
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3
                    [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-sm
                    bg-secondary/50"
                  style={{
                    background: `linear-gradient(to right, ${color}40 0%, ${color}40 ${(w / 3) * 100}%, rgba(255,255,255,0.06) ${(w / 3) * 100}%, rgba(255,255,255,0.06) 100%)`,
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
