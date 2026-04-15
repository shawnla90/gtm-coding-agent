"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, ExternalLink, Copy, Check, Sparkles, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { MagneticButton } from "@/components/unlumen/magnetic-button";
import { GlowButton } from "@/components/unlumen/glow-button";
import { LinkedInAvatar } from "@/components/linkedin-avatar";
import {
  signalTypeLabels,
  signalTypeColors,
  signalTypeSdrAngles,
  urgencyColors,
  truncate,
  platformIcons,
} from "@/lib/format";
import type { SignalWithContent, SignalLead } from "@/lib/db";

interface Props {
  signals: SignalWithContent[];
  leadsMap: Record<number, SignalLead[]>;
  reasoningMap?: Record<number, Record<number, string>>;
  commentsMap?: Record<number, Record<number, string>>;
  insightsMap?: Record<number, { outreach_angle: string; opener_draft: string }>;
  weights?: Record<string, number>;
}

// Urgency rank for sorting
const URGENCY_RANK: Record<string, number> = {
  "act-now": 1,
  "this-week": 2,
  "this-month": 3,
  backlog: 4,
};

function sortSignals(
  signals: SignalWithContent[],
  weights: Record<string, number>,
): SignalWithContent[] {
  const hasWeights = Object.keys(weights).length > 0;
  if (!hasWeights) return signals;

  return [...signals].sort((a, b) => {
    const wA = weights[a.signal_type] ?? 1;
    const wB = weights[b.signal_type] ?? 1;
    const scoreA = (5 - (URGENCY_RANK[a.urgency] ?? 4)) * wA;
    const scoreB = (5 - (URGENCY_RANK[b.urgency] ?? 4)) * wB;
    return scoreB - scoreA;
  });
}

export function SignalAccordion({
  signals,
  leadsMap,
  reasoningMap = {},
  commentsMap = {},
  insightsMap = {},
  weights = {},
}: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const sorted = sortSignals(signals, weights);

  return (
    <div className="space-y-2">
      {sorted.map((sig) => (
        <SignalCard
          key={sig.id}
          signal={sig}
          leads={leadsMap[sig.id] ?? []}
          reasoning={reasoningMap[sig.id] ?? {}}
          comments={commentsMap[sig.id] ?? {}}
          insight={insightsMap[sig.id]}
          isExpanded={expandedId === sig.id}
          onToggle={() =>
            setExpandedId(expandedId === sig.id ? null : sig.id)
          }
        />
      ))}
    </div>
  );
}

function SignalCard({
  signal,
  leads,
  reasoning,
  comments,
  insight,
  isExpanded,
  onToggle,
}: {
  signal: SignalWithContent;
  leads: SignalLead[];
  reasoning: Record<number, string>;
  comments: Record<number, string>;
  insight?: { outreach_angle: string; opener_draft: string };
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [expandedLeadId, setExpandedLeadId] = useState<number | null>(null);
  const [showReasoningFor, setShowReasoningFor] = useState<number | null>(null);

  const typeLabel = signalTypeLabels[signal.signal_type] ?? signal.signal_type;
  const typeColor = signalTypeColors[signal.signal_type] ?? "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
  const sdrAngle = signalTypeSdrAngles[signal.signal_type] ?? "";

  // Use pipeline insight if available, else static angle
  const displayAngle = insight?.outreach_angle ?? sdrAngle;
  const openerDraft = insight?.opener_draft;

  const urgencyBar =
    signal.urgency === "act-now"
      ? "bg-red-500"
      : signal.urgency === "this-week"
        ? "bg-orange-500"
        : signal.urgency === "this-month"
          ? "bg-yellow-500"
          : "bg-zinc-500";

  function handleCopy() {
    const parts = [signal.title, "", displayAngle];
    if (openerDraft) parts.push("", `Opener: ${openerDraft}`);
    parts.push("", `Source: ${signal.source_name ?? "Unknown"}`, signal.content_url ?? "");
    navigator.clipboard.writeText(parts.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <MagneticButton className="w-full" radius={80} strength={0.15}>
      <motion.div
        layout
        className="overflow-hidden rounded-xl border border-border/50 bg-card/80 backdrop-blur-sm"
        id={`signal-${signal.id}`}
      >
        {/* Collapsed header */}
        <button
          onClick={onToggle}
          className="flex w-full items-center gap-3 px-4 py-3 text-left"
        >
          <div className={cn("h-10 w-1 rounded-full shrink-0", urgencyBar)} />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span
                className={cn(
                  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                  typeColor
                )}
              >
                {typeLabel}
              </span>
              {signal.post_age_days !== null && (
                <span className="text-[10px] text-muted-foreground">
                  {signal.post_age_days}d ago
                </span>
              )}
            </div>
            <p className="text-sm font-medium truncate">{signal.title}</p>
            <p className="text-xs text-muted-foreground truncate">
              {signal.source_name}
              {signal.platform && ` · ${platformIcons[signal.platform] ?? signal.platform}`}
            </p>
          </div>

          {/* Lead count */}
          {signal.lead_count > 0 && (
            <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
              {signal.lead_count} leads
            </span>
          )}

          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="shrink-0"
          >
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </motion.div>
        </button>

        {/* Expanded content */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{
                height: { type: "spring", stiffness: 300, damping: 28 },
                opacity: { duration: 0.2 },
              }}
              className="overflow-hidden"
            >
              <div className="border-t border-border/30 px-4 pb-4 pt-3 space-y-4">
                {/* Signal description */}
                {signal.description && (
                  <p className="text-xs text-muted-foreground/80 leading-relaxed">
                    {signal.description}
                  </p>
                )}

                {/* Section 1: Source content */}
                {signal.content_body && (
                  <div className="rounded-lg bg-secondary/30 p-3">
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {truncate(signal.content_body, 280)}
                    </p>
                    <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground">
                      {signal.content_likes > 0 && (
                        <span>{signal.content_likes} likes</span>
                      )}
                      {signal.content_comments > 0 && (
                        <span>{signal.content_comments} comments</span>
                      )}
                      {signal.content_url && (
                        <a
                          href={signal.content_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-0.5 text-primary hover:underline"
                        >
                          View post <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {/* Section 2: ICP Leads cluster */}
                {leads.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      ICP Leads
                    </h4>
                    <div className="space-y-2">
                      {leads.map((lead) => {
                        const comment = comments[lead.id];
                        const reasoningText = reasoning[lead.id];
                        const isLeadExpanded = expandedLeadId === lead.id;
                        const isReasoningShown = showReasoningFor === lead.id;

                        return (
                          <div key={lead.id}>
                            <div className="flex items-center gap-2">
                              <GlowButton
                                mode="breathe"
                                colors={["#D4A843", "#B8922E", "#D4A843"]}
                                blur="blur-sm"
                                duration={4}
                                glowScale={1.05}
                                className="shrink-0"
                              >
                                <a
                                  href={lead.profile_url ?? "#"}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-2 rounded-lg border border-border/50 bg-card px-3 py-2"
                                >
                                  <LinkedInAvatar
                                    name={lead.name ?? "?"}
                                    size="sm"
                                  />
                                  <div className="min-w-0">
                                    <p className="text-xs font-medium truncate max-w-[120px]">
                                      {lead.name ?? "Unknown"}
                                    </p>
                                    <p className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                                      {lead.title ?? lead.company ?? ""}
                                    </p>
                                  </div>
                                  <span className="ml-1 text-[10px] font-bold text-primary">
                                    {lead.overall_stars}★
                                  </span>
                                </a>
                              </GlowButton>

                              {/* Engagement toggle */}
                              {comment && (
                                <button
                                  onClick={() =>
                                    setExpandedLeadId(isLeadExpanded ? null : lead.id)
                                  }
                                  className={cn(
                                    "rounded-md p-1 transition-colors",
                                    isLeadExpanded ? "bg-secondary/50 text-foreground" : "text-muted-foreground hover:text-foreground",
                                  )}
                                  title="Show engagement"
                                >
                                  <MessageCircle className="h-3 w-3" />
                                </button>
                              )}

                              {/* Why? chip */}
                              {reasoningText && (
                                <button
                                  onClick={() =>
                                    setShowReasoningFor(isReasoningShown ? null : lead.id)
                                  }
                                  className={cn(
                                    "rounded-md border px-1.5 py-0.5 text-[9px] font-bold transition-colors",
                                    isReasoningShown
                                      ? "border-primary/40 bg-primary/15 text-primary"
                                      : "border-primary/20 bg-primary/5 text-primary/70 hover:text-primary hover:bg-primary/10",
                                  )}
                                >
                                  Why?
                                </button>
                              )}
                            </div>

                            {/* Expanded comment */}
                            <AnimatePresence>
                              {isLeadExpanded && comment && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: "auto", opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.15 }}
                                  className="overflow-hidden"
                                >
                                  <div className="ml-4 mt-1.5 rounded-lg border border-border/30 bg-secondary/20 p-2.5">
                                    <p className="text-xs text-foreground/80 leading-relaxed italic">
                                      &ldquo;{comment}&rdquo;
                                    </p>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>

                            {/* Reasoning */}
                            <AnimatePresence>
                              {isReasoningShown && reasoningText && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: "auto", opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.15 }}
                                  className="overflow-hidden"
                                >
                                  <div className="ml-4 mt-1.5 rounded-lg border border-primary/20 bg-primary/5 p-2.5">
                                    <p className="text-xs text-foreground/80 leading-relaxed">
                                      {reasoningText}
                                    </p>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Section 3: SDR Suggestion */}
                {displayAngle && (
                  <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                    <div className="flex items-start gap-2">
                      <Sparkles className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
                      <div className="flex-1 space-y-2">
                        <p className="text-xs font-medium text-primary mb-1">
                          {insight ? "AI-Generated Outreach Angle" : "SDR Suggestion"}
                        </p>
                        <p className="text-xs text-foreground/80 leading-relaxed">
                          {displayAngle}
                        </p>
                        {openerDraft && (
                          <div className="rounded-md border border-border/30 bg-card/50 p-2.5">
                            <p className="text-[10px] font-medium text-muted-foreground mb-1">
                              Draft Opener
                            </p>
                            <p className="text-xs text-foreground/90 leading-relaxed">
                              {openerDraft}
                            </p>
                          </div>
                        )}
                      </div>
                      <button
                        onClick={handleCopy}
                        className="shrink-0 rounded-md p-1.5 hover:bg-primary/10 transition-colors"
                        title="Copy to clipboard"
                      >
                        {copied ? (
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </MagneticButton>
  );
}
