"use client";

import Link from "next/link";
import { ExternalLink, Sparkles, ArrowRight } from "lucide-react";
import { LinkedInAvatar } from "@/components/linkedin-avatar";
import {
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  signalTypeLabels,
  signalTypeColors,
  signalTypeSdrAngles,
  platformIcons,
  truncate,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SignalDrawerData, DrawerTarget } from "./types";

interface Props {
  data: SignalDrawerData;
  onSwap: (target: DrawerTarget) => void;
}

export function SignalDrawer({ data, onSwap }: Props) {
  const typeLabel = signalTypeLabels[data.signal_type] ?? data.signal_type;
  const typeColor =
    signalTypeColors[data.signal_type] ??
    "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
  const sdrAngle = signalTypeSdrAngles[data.signal_type] ?? "";
  const displayAngle = data.outreach_angle ?? sdrAngle;

  const urgencyBar =
    data.urgency === "act-now"
      ? "bg-red-500"
      : data.urgency === "this-week"
        ? "bg-orange-500"
        : data.urgency === "this-month"
          ? "bg-yellow-500"
          : "bg-zinc-500";

  return (
    <>
      <SheetHeader>
        <div className="flex items-start gap-3">
          <div className={cn("h-12 w-1 rounded-full shrink-0", urgencyBar)} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={cn(
                  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                  typeColor,
                )}
              >
                {typeLabel}
              </span>
              {data.post_age_days !== null && (
                <span className="text-[10px] text-muted-foreground">
                  {data.post_age_days}d ago
                </span>
              )}
            </div>
            <SheetTitle className="text-left leading-tight text-base">
              {data.title}
            </SheetTitle>
            <SheetDescription className="text-left">
              {data.source_name ?? "Unknown source"}
              {data.platform &&
                ` · ${platformIcons[data.platform] ?? data.platform}`}
            </SheetDescription>
          </div>
        </div>
      </SheetHeader>

      {/* AI description */}
      {data.description && (
        <div className="px-4">
          <p className="text-xs text-muted-foreground/80 leading-relaxed">
            {data.description}
          </p>
        </div>
      )}

      {/* Source content excerpt */}
      {data.content_body && (
        <div className="px-4">
          <div className="rounded-lg bg-secondary/30 p-3">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {truncate(data.content_body, 280)}
            </p>
            <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground">
              {data.content_likes > 0 && (
                <span>{data.content_likes} likes</span>
              )}
              {data.content_comments > 0 && (
                <span>{data.content_comments} comments</span>
              )}
              {data.content_url && (
                <a
                  href={data.content_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-0.5 text-primary hover:underline"
                >
                  View post <ExternalLink className="h-2.5 w-2.5" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ICP Leads — clickable to swap to engager drawer */}
      {data.leads.length > 0 && (
        <div className="px-4 space-y-2">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            ICP Leads ({data.leads.length})
          </h4>
          <div className="space-y-1.5">
            {data.leads.map((lead) => (
              <button
                key={lead.id}
                type="button"
                onClick={() => onSwap({ type: "engager", id: lead.id })}
                className="flex w-full items-center gap-2 rounded-lg border border-border/50 bg-card/50 px-2.5 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
              >
                <LinkedInAvatar
                  name={lead.name}
                  imageUrl={lead.profile_image_url}
                  size="sm"
                  platform={lead.platform as "linkedin" | "x" | "reddit"}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium truncate">
                    {lead.name ?? "Unknown"}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {lead.title ?? lead.company ?? ""}
                  </p>
                </div>
                <span className="shrink-0 text-[10px] font-bold text-primary">
                  {lead.overall_stars}★
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* SDR / AI outreach angle */}
      {displayAngle && (
        <div className="px-4">
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
            <div className="flex items-start gap-2">
              <Sparkles className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
              <div className="flex-1 space-y-2">
                <p className="text-xs font-medium text-primary">
                  {data.outreach_angle ? "AI Outreach Angle" : "SDR Suggestion"}
                </p>
                <p className="text-xs text-foreground/80 leading-relaxed">
                  {displayAngle}
                </p>
                {data.opener_draft && (
                  <div className="rounded-md border border-border/30 bg-card/50 p-2.5 mt-2">
                    <p className="text-[10px] font-medium text-muted-foreground mb-1">
                      Draft Opener
                    </p>
                    <p className="text-xs text-foreground/90 leading-relaxed">
                      {data.opener_draft}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View full signal CTA */}
      <div className="px-4 pb-4">
        <Link
          href={`/signals?highlight=${data.id}`}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary/20"
        >
          View full signal
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </>
  );
}
