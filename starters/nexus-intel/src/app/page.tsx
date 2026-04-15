import Link from "next/link";
import {
  getKpiDeltas,
  getEngagementTrend,
  getSignalsWithLeadCounts,
  getLatestScrapeTime,
  getSourceCounts,
  getFreshSignalCount,
} from "@/lib/db";
import { formatNum, urgencyColors, signalTypeLabels } from "@/lib/format";
import { KpiCard } from "@/components/kpi-card";
import { TiltCard } from "@/components/unlumen/tilt-card";
import { MomentumChart } from "@/components/momentum-chart";
import { FreshnessBadge } from "@/components/freshness-badge";
import {
  Zap,
  ArrowRight,
} from "lucide-react";

export const dynamic = "force-dynamic";

export default function CommandCenter() {
  const kpis = getKpiDeltas();
  const trend = getEngagementTrend(8);
  const topSignals = getSignalsWithLeadCounts({ limit: 5 });
  const latestScrape = getLatestScrapeTime();
  const sourceCounts = getSourceCounts();
  const freshSignals = getFreshSignalCount();

  return (
    <div className="flex-1 p-6 md:p-8 max-w-6xl mx-auto w-full space-y-8">
      {/* Hero header */}
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Command Center
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sales intelligence signals for the GTM space
          </p>
        </div>
        <FreshnessBadge completedAt={latestScrape} />
      </header>

      {/* KPI strip — 3 TiltCards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <TiltCard>
          <KpiCard
            label="Active Signals"
            value={freshSignals}
            delta={kpis.signals_delta}
            sparkline={kpis.signals_sparkline}
            accent="emerald"
          />
        </TiltCard>
        <TiltCard>
          <KpiCard
            label="ICP Leads (4★+)"
            value={kpis.active_threats}
            delta={kpis.active_threats_delta}
            sparkline={kpis.threats_sparkline}
            accent="rose"
          />
        </TiltCard>
        <TiltCard>
          <KpiCard
            label="Sources Tracked"
            value={sourceCounts.total}
            delta={kpis.content_delta}
            sparkline={kpis.content_sparkline}
            accent="cyan"
          />
        </TiltCard>
      </div>

      {/* Momentum chart */}
      <section className="rounded-xl border border-border/50 bg-card p-5">
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          Engagement Momentum (8 weeks)
        </h2>
        <MomentumChart data={trend} />
      </section>

      {/* Top 5 signals preview */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-muted-foreground">
            Top Signals
          </h2>
          <Link
            href="/signals"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="space-y-2">
          {topSignals.map((sig) => (
            <Link
              key={sig.id}
              href={`/signals?highlight=${sig.id}`}
              className="group flex items-center gap-3 rounded-lg border border-border/40 bg-card/50 px-4 py-3 transition-colors hover:bg-card"
            >
              {/* Urgency bar */}
              <div
                className={`h-8 w-1 rounded-full ${
                  sig.urgency === "act-now"
                    ? "bg-red-500"
                    : sig.urgency === "this-week"
                      ? "bg-orange-500"
                      : sig.urgency === "this-month"
                        ? "bg-yellow-500"
                        : "bg-zinc-500"
                }`}
              />

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                  {sig.title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {signalTypeLabels[sig.signal_type] ?? sig.signal_type}
                  {sig.source_name && ` · ${sig.source_name}`}
                </p>
              </div>

              {/* Lead count */}
              {sig.lead_count > 0 && (
                <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  <Zap className="h-2.5 w-2.5" />
                  {sig.lead_count} leads
                </span>
              )}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
