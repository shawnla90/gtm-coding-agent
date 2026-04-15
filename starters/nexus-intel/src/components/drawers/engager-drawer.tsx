"use client";

import { LinkedInAvatar } from "@/components/linkedin-avatar";
import {
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import type { EngagerDrawerData } from "./types";

interface Props {
  data: EngagerDrawerData;
}

export function EngagerDrawer({ data }: Props) {
  return (
    <>
      <SheetHeader>
        <div className="flex items-center gap-3">
          <LinkedInAvatar
            name={data.name}
            imageUrl={data.profileImageUrl}
            size="xl"
            platform={data.platform as "linkedin" | "x" | "reddit"}
          />
          <div className="min-w-0 flex-1">
            <SheetTitle className="truncate">
              {data.name ?? "Unknown"}
            </SheetTitle>
            <SheetDescription className="truncate">
              {data.title ?? ""}
            </SheetDescription>
            {data.company && (
              <p className="text-xs text-muted-foreground/70 truncate">
                {data.company}
              </p>
            )}
          </div>
          {data.stars != null && (
            <span className="shrink-0 rounded-full bg-primary/10 px-2.5 py-1 text-sm font-bold text-primary">
              {data.stars}★
            </span>
          )}
        </div>
      </SheetHeader>

      {/* Engagement trail */}
      {data.engagements.length > 0 && (
        <div className="px-4 space-y-2">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Engagement Trail
          </h4>
          <div className="space-y-2 max-h-[240px] overflow-y-auto">
            {data.engagements.map((eng) => (
              <div
                key={eng.id}
                className="rounded-lg border border-border/30 bg-secondary/20 p-2.5"
              >
                {eng.comment_text ? (
                  <p className="text-xs text-foreground/80 leading-relaxed">
                    &ldquo;{eng.comment_text}&rdquo;
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground italic">
                    {eng.engagement_type === "like" ? "Liked this post" : "Reposted"}
                  </p>
                )}
                <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                  {eng.source_name && <span>{eng.source_name}</span>}
                  {eng.post_url && (
                    <a
                      href={eng.post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      View post
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Reasoning */}
      {data.reasoning.length > 0 && (
        <div className="px-4 space-y-2">
          <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Why This Person Matters
          </h4>
          <div className="space-y-2">
            {data.reasoning.map((r, i) => (
              <div
                key={i}
                className="rounded-lg border border-primary/20 bg-primary/5 p-2.5"
              >
                {r.signal_title && (
                  <p className="text-[10px] font-medium text-primary mb-1 truncate">
                    {r.signal_title}
                  </p>
                )}
                <p className="text-xs text-foreground/80 leading-relaxed">
                  {r.reasoning}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View Profile CTA */}
      {data.profileUrl && (
        <div className="px-4 pb-4">
          <a
            href={data.profileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary/20"
          >
            View Profile
          </a>
        </div>
      )}
    </>
  );
}
