"use client";

import { ExternalLink } from "lucide-react";
import { LinkedInAvatar } from "@/components/linkedin-avatar";
import {
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  signalTypeLabels,
  signalTypeColors,
  truncate,
  formatNum,
  relativeTime,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SourceDrawerData, DrawerTarget } from "./types";

interface Props {
  data: SourceDrawerData;
  onSwap: (target: DrawerTarget) => void;
}

const relevanceColors: Record<string, string> = {
  competitor: "bg-red-500/10 text-red-400 border-red-500/20",
  "thought-leader": "bg-amber-500/10 text-amber-400 border-amber-500/20",
  founder: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  other: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

const relevanceLabels: Record<string, string> = {
  competitor: "Competitor",
  "thought-leader": "Thought Leader",
  founder: "Founder",
  other: "Other",
};

const urgencyBarColor: Record<string, string> = {
  "act-now": "bg-emerald-500",
  "this-week": "bg-emerald-400",
  "this-month": "bg-emerald-300",
  backlog: "bg-emerald-200",
};

export function SourceDrawer({ data, onSwap }: Props) {
  const relevanceLabel =
    relevanceLabels[data.relevance ?? ""] ?? data.relevance ?? "Source";
  const relevanceColor =
    relevanceColors[data.relevance ?? ""] ?? relevanceColors.other;

  return (
    <>
      <SheetHeader>
        <div className="flex items-start gap-3">
          <LinkedInAvatar
            name={data.name}
            imageUrl={data.profileImageUrl}
            size="xl"
            platform={data.platform as "linkedin" | "x" | "reddit"}
          />
          <div className="min-w-0 flex-1">
            <div className="mb-1">
              <span
                className={cn(
                  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                  relevanceColor,
                )}
              >
                {relevanceLabel}
              </span>
            </div>
            <SheetTitle className="truncate">{data.name}</SheetTitle>
            <SheetDescription className="truncate">
              {data.title ?? data.handle ?? ""}
              {data.company && ` · ${data.company}`}
            </SheetDescription>
            {data.followers != null && data.followers > 0 && (
              <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                {formatNum(data.followers)} followers
              </p>
            )}
          </div>
        </div>
      </SheetHeader>

      {/* Stats row */}
      <div className="px-4">
        <div className="grid grid-cols-3 gap-2 rounded-lg bg-secondary/30 p-3">
          <Stat label="Posts" value={data.stats.total_posts} />
          <Stat label="Signals" value={data.stats.signal_count} />
          <Stat label="ICP engagers" value={data.stats.icp_engager_count} />
        </div>
      </div>

      {/* Recent content */}
      {data.recentContent.length > 0 && (
        <div className="px-4 space-y-2">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Recent Content ({data.recentContent.length})
          </h4>
          <div className="space-y-2">
            {data.recentContent.map((c) => (
              <div
                key={c.id}
                className="rounded-lg border border-border/30 bg-secondary/20 p-2.5"
              >
                {c.title && (
                  <p className="text-xs font-medium mb-1 line-clamp-2">
                    {c.title}
                  </p>
                )}
                {c.body && (
                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                    {truncate(c.body, 200)}
                  </p>
                )}
                <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                  {c.published_at && <span>{relativeTime(c.published_at)}</span>}
                  {c.engagement_likes > 0 && (
                    <span>{c.engagement_likes} likes</span>
                  )}
                  {c.engagement_comments > 0 && (
                    <span>{c.engagement_comments} comments</span>
                  )}
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 text-primary hover:underline ml-auto"
                    >
                      View <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Signals generated */}
      {data.signals.length > 0 && (
        <div className="px-4 space-y-2">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Signals Generated
          </h4>
          <div className="space-y-1.5">
            {data.signals.map((sig) => (
              <button
                key={sig.id}
                type="button"
                onClick={() => onSwap({ type: "signal", id: sig.id })}
                className="flex w-full items-center gap-2 rounded-lg border border-border/50 bg-card/50 px-2.5 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
              >
                <div
                  className={cn(
                    "h-8 w-0.5 rounded-full shrink-0",
                    urgencyBarColor[sig.urgency] ?? "bg-emerald-200",
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1 mb-0.5">
                    <span
                      className={cn(
                        "inline-flex items-center rounded border px-1 py-0 text-[9px] font-medium",
                        signalTypeColors[sig.signal_type] ??
                          "border-zinc-500/20",
                      )}
                    >
                      {signalTypeLabels[sig.signal_type] ?? sig.signal_type}
                    </span>
                    {sig.post_age_days !== null && (
                      <span className="text-[9px] text-muted-foreground">
                        {sig.post_age_days}d
                      </span>
                    )}
                  </div>
                  <p className="text-xs truncate">{sig.title}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ICP engagers */}
      {data.topEngagers.length > 0 && (
        <div className="px-4 space-y-2">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Top ICP Engagers
          </h4>
          <div className="space-y-1.5">
            {data.topEngagers.map((eng) => (
              <button
                key={eng.id}
                type="button"
                onClick={() => onSwap({ type: "engager", id: eng.id })}
                className="flex w-full items-center gap-2 rounded-lg border border-border/50 bg-card/50 px-2.5 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
              >
                <LinkedInAvatar
                  name={eng.name}
                  imageUrl={eng.profile_image_url}
                  size="sm"
                  platform={eng.platform as "linkedin" | "x" | "reddit"}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium truncate">
                    {eng.name ?? "Unknown"}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {eng.title ?? eng.company ?? ""}
                  </p>
                </div>
                <span className="shrink-0 text-[10px] font-bold text-primary">
                  {eng.overall_stars}★
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* View profile CTA */}
      {data.profileUrl && (
        <div className="px-4 pb-4">
          <a
            href={data.profileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary/20"
          >
            View Profile
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center">
      <p className="text-base font-bold text-foreground">{value}</p>
      <p className="text-[9px] text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
    </div>
  );
}
