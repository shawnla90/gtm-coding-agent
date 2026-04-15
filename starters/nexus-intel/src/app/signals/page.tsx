import { Suspense } from "react";
import {
  getSignalsWithLeadCounts,
  getLeadsForSignal,
  getLatestScrapeTime,
  getSignalCountsByType,
  getLeadReasoningForSignals,
  getCommentsForSignals,
  getInsightsForSignals,
} from "@/lib/db";
import { FreshnessBadge } from "@/components/freshness-badge";
import { SignalFilters } from "@/components/signal-filters";
import { SignalsClient } from "./signals-client";

export const dynamic = "force-dynamic";

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: Promise<{ urgency?: string; type?: string; highlight?: string }>;
}) {
  const params = await searchParams;
  const urgencyFilter = params.urgency ?? "all";
  const typeFilter = params.type;

  const signals = getSignalsWithLeadCounts({
    urgency: urgencyFilter as "act-now" | "this-week" | "this-month" | "backlog" | "all",
    signalType: typeFilter,
    limit: 40,
  });

  // Pre-fetch leads for each signal (batch)
  const leadsMap: Record<number, Awaited<ReturnType<typeof getLeadsForSignal>>> = {};
  for (const sig of signals) {
    if (sig.lead_count > 0) {
      leadsMap[sig.id] = getLeadsForSignal(sig.id, 8);
    }
  }

  const latestScrape = getLatestScrapeTime();
  const typeCounts = getSignalCountsByType();

  // Fetch reasoning, comments, and insights for all signals in view
  const signalIds = signals.map((s) => s.id);
  const reasoningMap = getLeadReasoningForSignals(signalIds);
  const commentsMap = getCommentsForSignals(signalIds);
  const insightsMap = getInsightsForSignals(signalIds);

  // Group by urgency
  const grouped = {
    "act-now": signals.filter((s) => s.urgency === "act-now"),
    "this-week": signals.filter((s) => s.urgency === "this-week"),
    "this-month": signals.filter((s) => s.urgency === "this-month"),
    backlog: signals.filter((s) => s.urgency === "backlog"),
  };

  const urgencyLabels: Record<string, string> = {
    "act-now": "Act Now",
    "this-week": "This Week",
    "this-month": "This Month",
    backlog: "Backlog",
  };

  const urgencyDotColors: Record<string, string> = {
    "act-now": "bg-red-500",
    "this-week": "bg-orange-500",
    "this-month": "bg-yellow-500",
    backlog: "bg-zinc-500",
  };

  return (
    <div className="flex-1 p-6 md:p-8 max-w-5xl mx-auto w-full space-y-6">
      {/* Header */}
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Signals</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {signals.length} actionable signals ·{" "}
            {signals.reduce((acc, s) => acc + s.lead_count, 0)} ICP leads connected
          </p>
        </div>
        <FreshnessBadge completedAt={latestScrape} />
      </header>

      {/* Filter chips */}
      <SignalFilters activeUrgency={urgencyFilter} activeType={typeFilter ?? "all"} />

      {/* Client-side: meter + accordion with weight-based sorting */}
      <Suspense fallback={null}>
        <SignalsClient
          signals={signals}
          leadsMap={leadsMap}
          reasoningMap={reasoningMap}
          commentsMap={commentsMap}
          insightsMap={insightsMap}
          typeCounts={typeCounts}
          grouped={grouped}
          urgencyLabels={urgencyLabels}
          urgencyDotColors={urgencyDotColors}
          urgencyFilter={urgencyFilter}
        />
      </Suspense>
    </div>
  );
}
