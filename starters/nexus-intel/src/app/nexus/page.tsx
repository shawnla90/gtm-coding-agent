import { getNexusData, getEngagerById, getEngagerEngagements, getLeadReasoning } from "@/lib/db";
import { Globe } from "lucide-react";
import { NexusClient } from "./nexus-client";

export const dynamic = "force-dynamic";

export default function NexusPage() {
  const data = getNexusData();

  // Transform db nexus data into force graph nodes/edges
  const nodes = [
    ...data.signals.map((s) => ({
      id: `signal-${s.id}`,
      label: s.title,
      subtitle: s.signal_type,
      type: "signal" as const,
      urgency: s.urgency,
    })),
    ...data.sources.map((s) => ({
      id: `source-${s.id}`,
      label: s.name,
      type: "source" as const,
      relevance: s.relevance,
      platform: s.platform,
      profileImageUrl: s.profile_image_url ?? undefined,
      sourceContentCount: 0,
      sourceSignalCount: s.signal_count,
    })),
    ...data.engagers.map((e) => ({
      id: `engager-${e.id}`,
      label: e.name ?? "Unknown",
      subtitle: e.company ?? undefined,
      type: "engager" as const,
      stars: e.stars ?? 0,
      profileImageUrl: e.profile_image_url ?? undefined,
      platform: e.platform,
      title: undefined as string | undefined,
      company: e.company ?? undefined,
    })),
  ];

  const edges = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    weight: e.weight,
  }));

  // Pre-serialize engager IDs for the client to fetch drawer data
  const engagerIds = data.engagers.map((e) => e.id);

  return (
    <div className="flex flex-1 flex-col p-6 md:p-8">
      <header className="mb-4 flex items-center gap-2">
        <Globe className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">Relationship Web</h1>
        <span className="ml-2 text-xs text-muted-foreground">
          {nodes.length} nodes · {edges.length} connections
        </span>
      </header>

      <div className="flex-1 rounded-xl border border-border/30 bg-card/30 overflow-hidden">
        <NexusClient nodes={nodes} edges={edges} />
      </div>
    </div>
  );
}
