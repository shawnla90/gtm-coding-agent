"use client";

import { ExternalLink } from "lucide-react";
import { GlowButton } from "@/components/unlumen/glow-button";
import { LinkedInAvatar } from "@/components/linkedin-avatar";
import { cn } from "@/lib/utils";
import type { Engager } from "@/lib/db";

export function LeadCard({ lead }: { lead: Engager }) {
  const stars = lead.overall_stars ?? 0;

  return (
    <div className="group rounded-xl border border-border/40 bg-card/60 p-4 transition-colors hover:bg-card hover:border-primary/20">
      <div className="flex items-start gap-3">
        <LinkedInAvatar
          name={lead.name ?? lead.handle}
          imageUrl={lead.profile_image_url}
          size="lg"
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {lead.name ?? lead.handle}
          </p>
          <p className="text-xs text-muted-foreground truncate">
            {lead.title ?? ""}
          </p>
          <p className="text-xs text-muted-foreground/70 truncate">
            {lead.company ?? lead.parsed_company ?? ""}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={cn(
              "text-xs font-bold",
              stars >= 4 ? "text-primary" : "text-muted-foreground"
            )}
          >
            {stars}★
          </span>
          {lead.engagement_count && lead.engagement_count > 0 && (
            <span className="text-[10px] text-muted-foreground">
              {lead.engagement_count} engagements
            </span>
          )}
        </div>
      </div>

      {/* Job bucket badge */}
      {lead.job_bucket && (
        <div className="mt-2">
          <span className="inline-block rounded-md bg-secondary/50 px-2 py-0.5 text-[10px] text-muted-foreground">
            {lead.job_bucket.replace(/-/g, " ")}
          </span>
        </div>
      )}

      {/* CTA */}
      {lead.profile_url && (
        <div className="mt-3">
          <GlowButton
            mode="breathe"
            colors={["#D4A843", "#B8922E", "#D4A843"]}
            blur="blur-sm"
            duration={4}
            glowScale={1.03}
          >
            <a
              href={lead.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
            >
              View Profile <ExternalLink className="h-3 w-3" />
            </a>
          </GlowButton>
        </div>
      )}
    </div>
  );
}
