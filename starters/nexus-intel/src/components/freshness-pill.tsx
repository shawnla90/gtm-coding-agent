/**
 * FreshnessPill — age badge for post-backed signals + insights.
 *
 * Server Component. Renders a small color-coded pill showing how old the
 * underlying post is. The buckets match the decay rules in scripts/_decay.py
 * so the UI never contradicts server-side truth.
 *
 * Prefer passing `ageDays` precomputed from the SQL query. If only
 * `publishedAt` is available the component will compute locally via Date.now(),
 * which is fine on dynamic pages (force-dynamic / no `use cache`) but will
 * freeze inside cached contexts — so always route `post_age_days` through the
 * DB layer when the page is cached.
 *
 * Freshness buckets (aligned with docs/freshness.md):
 *   < 7 days   — fresh       (emerald)
 *   7–21 days  — actionable  (amber)
 *   21–60 days — aging       (zinc)
 *   60–180 days — stale      (rose)
 *   180+ days  — ancient     (red, strike-through)
 */

type Bucket = "fresh" | "actionable" | "aging" | "stale" | "ancient" | "unknown";

const BUCKET_STYLE: Record<Bucket, { cls: string; title: string }> = {
  fresh: {
    cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    title: "Fresh (< 7 days old)",
  },
  actionable: {
    cls: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    title: "Actionable (7–21 days old)",
  },
  aging: {
    cls: "border-zinc-500/40 bg-zinc-500/10 text-zinc-300",
    title: "Aging (21–60 days old)",
  },
  stale: {
    cls: "border-rose-500/40 bg-rose-500/10 text-rose-400",
    title: "Stale (60–180 days old)",
  },
  ancient: {
    cls: "border-red-600/50 bg-red-600/10 text-red-500 line-through",
    title: "Ancient (> 180 days — likely dead)",
  },
  unknown: {
    cls: "border-border bg-background text-muted-foreground",
    title: "Unknown post date",
  },
};

function bucketFor(ageDays: number): Bucket {
  if (ageDays < 7) return "fresh";
  if (ageDays < 21) return "actionable";
  if (ageDays < 60) return "aging";
  if (ageDays < 180) return "stale";
  return "ancient";
}

function labelFor(ageDays: number): string {
  if (ageDays < 1) return "today";
  if (ageDays < 7) return `${ageDays}d`;
  if (ageDays < 30) return `${Math.floor(ageDays / 7)}w`;
  if (ageDays < 365) return `${Math.floor(ageDays / 30)}mo`;
  return `${Math.floor(ageDays / 365)}y+`;
}

function computeAgeDays(publishedAt: string): number | null {
  // Normalize SQLite "YYYY-MM-DD HH:MM:SS" → ISO with Z
  const iso =
    publishedAt.replace(" ", "T") + (publishedAt.includes("Z") || publishedAt.includes("+") ? "" : "Z");
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((Date.now() - t) / (1000 * 60 * 60 * 24)));
}

export function FreshnessPill({
  publishedAt,
  ageDays,
  className = "",
}: {
  publishedAt: string | null;
  ageDays?: number | null;
  className?: string;
}) {
  let age: number | null = null;
  if (typeof ageDays === "number" && Number.isFinite(ageDays)) {
    age = Math.max(0, Math.floor(ageDays));
  } else if (publishedAt) {
    age = computeAgeDays(publishedAt);
  }

  const bucket: Bucket = age === null ? "unknown" : bucketFor(age);
  const style = BUCKET_STYLE[bucket];
  const label = age === null ? "?" : labelFor(age);

  return (
    <span
      className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-medium leading-none ${style.cls} ${className}`}
      title={style.title}
    >
      {label}
    </span>
  );
}

/**
 * Helper exported alongside the component so pages can use the same
 * bucket boundaries to decide when to dim, hide, or strike a card.
 */
export function freshnessBucket(ageDays: number | null | undefined): Bucket {
  if (typeof ageDays !== "number" || !Number.isFinite(ageDays)) return "unknown";
  return bucketFor(Math.max(0, Math.floor(ageDays)));
}

export function isStaleAge(ageDays: number | null | undefined): boolean {
  if (typeof ageDays !== "number" || !Number.isFinite(ageDays)) return false;
  return ageDays >= 60;
}
