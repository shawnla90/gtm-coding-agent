"use client";

import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Gauge } from "lucide-react";
import { SignalAccordion } from "@/components/signal-accordion";
import { SignalMeter } from "@/components/signal-meter";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { SignalWithContent, SignalLead } from "@/lib/db";

interface Props {
  signals: SignalWithContent[];
  leadsMap: Record<number, SignalLead[]>;
  reasoningMap: Record<number, Record<number, string>>;
  commentsMap: Record<number, Record<number, string>>;
  insightsMap: Record<number, { outreach_angle: string; opener_draft: string }>;
  typeCounts: { signal_type: string; count: number }[];
  grouped: Record<string, SignalWithContent[]>;
  urgencyLabels: Record<string, string>;
  urgencyDotColors: Record<string, string>;
  urgencyFilter: string;
}

export function SignalsClient({
  signals,
  leadsMap,
  reasoningMap,
  commentsMap,
  insightsMap,
  typeCounts,
  grouped,
  urgencyLabels,
  urgencyDotColors,
  urgencyFilter,
}: Props) {
  const [meterOpen, setMeterOpen] = useState(false);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const searchParams = useSearchParams();
  const highlight = searchParams.get("highlight");

  const handleWeightsChange = useCallback((w: Record<string, number>) => {
    setWeights(w);
  }, []);

  // Scroll-to + pulse the highlighted signal when arriving from the nexus drawer
  useEffect(() => {
    if (!highlight) return;
    const el = document.getElementById(`signal-${highlight}`);
    if (!el) return;
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    el.classList.add("signal-pulse");
    const t = setTimeout(() => el.classList.remove("signal-pulse"), 2000);
    return () => clearTimeout(t);
  }, [highlight]);

  return (
    <>
      {/* Meter toggle button */}
      <div className="flex justify-end -mt-2">
        <button
          onClick={() => setMeterOpen(true)}
          className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-card/80 px-3 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur-sm transition-colors hover:text-foreground hover:border-primary/30"
        >
          <Gauge className="h-3.5 w-3.5" />
          Signal Meter
        </button>
      </div>

      {/* Signal meter drawer */}
      <Sheet open={meterOpen} onOpenChange={setMeterOpen}>
        <SheetContent side="right" className="w-[340px] sm:max-w-[380px]">
          <SheetHeader>
            <SheetTitle>Signal Meter</SheetTitle>
          </SheetHeader>
          <SignalMeter
            typeCounts={typeCounts}
            onWeightsChange={handleWeightsChange}
          />
        </SheetContent>
      </Sheet>

      {/* Grouped signal feed */}
      {urgencyFilter === "all" ? (
        <div className="space-y-8">
          {(["act-now", "this-week", "this-month", "backlog"] as const).map(
            (urg) =>
              grouped[urg].length > 0 && (
                <section key={urg}>
                  <div className="mb-3 flex items-center gap-2">
                    <div className={`h-2 w-2 rounded-full ${urgencyDotColors[urg]}`} />
                    <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {urgencyLabels[urg]} ({grouped[urg].length})
                    </h2>
                  </div>
                  <SignalAccordion
                    signals={grouped[urg]}
                    leadsMap={leadsMap}
                    reasoningMap={reasoningMap}
                    commentsMap={commentsMap}
                    insightsMap={insightsMap}
                    weights={weights}
                  />
                </section>
              )
          )}
        </div>
      ) : (
        <SignalAccordion
          signals={signals}
          leadsMap={leadsMap}
          reasoningMap={reasoningMap}
          commentsMap={commentsMap}
          insightsMap={insightsMap}
          weights={weights}
        />
      )}
    </>
  );
}
