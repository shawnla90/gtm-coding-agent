import { getEngagers, getEngagerCount, getEngagerBucketCounts } from "@/lib/db";
import { LeadCard } from "@/components/lead-card";
import { Users } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function LeadsPage({
  searchParams,
}: {
  searchParams: Promise<{ stars?: string; bucket?: string }>;
}) {
  const params = await searchParams;
  const minStars = params.stars ? parseInt(params.stars, 10) : 4;
  const jobBucket = params.bucket;

  const leads = getEngagers({
    minStars,
    jobBucket: jobBucket || undefined,
    hideInternal: true,
    limit: 60,
  });

  const totalCount = getEngagerCount({ minStars, hideInternal: true });
  const buckets = getEngagerBucketCounts(true, true);

  return (
    <div className="flex-1 p-6 md:p-8 max-w-6xl mx-auto w-full space-y-6">
      <header>
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">ICP Leads</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {totalCount} high-fit leads ({minStars}★+) across {buckets.length} job buckets
        </p>
      </header>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {[3, 4, 5].map((s) => (
          <a
            key={s}
            href={`/leads?stars=${s}${jobBucket ? `&bucket=${jobBucket}` : ""}`}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              minStars === s
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {s}★+
          </a>
        ))}
        <span className="mx-2 border-l border-border" />
        <a
          href={`/leads?stars=${minStars}`}
          className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
            !jobBucket
              ? "border-primary bg-primary/10 text-primary"
              : "border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          All Roles
        </a>
        {buckets.slice(0, 6).map((b) => (
          <a
            key={b.job_bucket}
            href={`/leads?stars=${minStars}&bucket=${b.job_bucket}`}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              jobBucket === b.job_bucket
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {b.job_bucket.replace(/-/g, " ")} ({b.count})
          </a>
        ))}
      </div>

      {/* Lead grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {leads.map((lead) => (
          <LeadCard key={lead.id} lead={lead} />
        ))}
      </div>

      {leads.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-12">
          No leads match these filters.
        </p>
      )}
    </div>
  );
}
