import { Badge } from "@/components/ui/badge";
import { relativeTime } from "@/lib/format";

function staleness(iso: string | null): "live" | "fresh" | "stale" {
  if (!iso) return "stale";
  const then = new Date(iso.replace(" ", "T") + (iso.includes("Z") ? "" : "Z"));
  const diffMin = (Date.now() - then.getTime()) / 60000;
  if (diffMin < 10) return "live";
  if (diffMin < 60 * 24) return "fresh";
  return "stale";
}

export function FreshnessBadge({
  completedAt,
  label = "Last scraped",
}: {
  completedAt: string | null;
  label?: string;
}) {
  const state = staleness(completedAt);
  const rel = relativeTime(completedAt);

  const dotColor =
    state === "live"
      ? "bg-emerald-500 animate-pulse"
      : state === "fresh"
        ? "bg-emerald-500/70"
        : "bg-zinc-500";

  return (
    <Badge
      variant="outline"
      className="gap-1.5 text-[10px] font-medium border-border/50 bg-background/40 backdrop-blur"
    >
      <span className={`size-1.5 rounded-full ${dotColor}`} />
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground">{rel}</span>
    </Badge>
  );
}
