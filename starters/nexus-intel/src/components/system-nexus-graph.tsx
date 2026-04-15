"use client";

import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeProps,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Dagre from "@dagrejs/dagre";
import type {
  NexusData,
  NexusEngagerNode,
  NexusSourceNode,
  NexusSignalNode,
} from "@/lib/db";

/* ─── Node data shapes (xyflow Node data payloads) ─── */

type EngagerData = {
  kind: "engager";
  engager: NexusEngagerNode;
  dim: boolean;
};
type SourceData = {
  kind: "source";
  source: NexusSourceNode;
  dim: boolean;
};
type SignalData = {
  kind: "signal";
  signal: NexusSignalNode;
  dim: boolean;
};

type NexusNodeData = EngagerData | SourceData | SignalData;

/* ─── Visual constants ─── */

const NODE_W = 200;
const NODE_H = 80;
const SIGNAL_NODE_W = 220;
const SIGNAL_NODE_H = 64;

const RELEVANCE_COLOR: Record<string, string> = {
  competitor: "border-red-500/50 bg-red-500/5",
  "thought-leader": "border-amber-500/50 bg-amber-500/5",
  founder: "border-violet-500/50 bg-violet-500/5",
  community: "border-blue-500/50 bg-blue-500/5",
  customer: "border-emerald-500/50 bg-emerald-500/5",
  "named-account": "border-primary/60 bg-primary/5",
};

const URGENCY_COLOR: Record<string, string> = {
  "act-now": "border-rose-500/60 bg-rose-500/10",
  "this-week": "border-amber-500/50 bg-amber-500/5",
  "this-month": "border-blue-500/40 bg-blue-500/5",
  backlog: "border-border/50 bg-card/30",
};

/* ─── Inline avatar renderer (client-safe, mirrors LinkedInAvatar minimum) ─── */

const GRADIENTS = [
  "from-blue-500 to-cyan-500",
  "from-violet-500 to-purple-500",
  "from-amber-500 to-rose-500",
  "from-emerald-500 to-teal-500",
  "from-pink-500 to-rose-500",
  "from-indigo-500 to-blue-500",
];

function gradientFor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0;
  return GRADIENTS[Math.abs(h) % GRADIENTS.length];
}

function initialsOf(name: string | null | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function InlineAvatar({
  name,
  imageUrl,
  size = 36,
}: {
  name: string | null;
  imageUrl: string | null | undefined;
  size?: number;
}) {
  if (imageUrl) {
    return (
      /* eslint-disable-next-line @next/next/no-img-element */
      <img
        src={imageUrl}
        alt={name ?? "avatar"}
        className="rounded-full ring-1 ring-border/60 object-cover shrink-0"
        style={{ width: size, height: size }}
        loading="lazy"
      />
    );
  }
  const gradient = gradientFor(name ?? "?");
  return (
    <span
      className={`inline-flex items-center justify-center rounded-full ring-1 ring-border/60 bg-gradient-to-br ${gradient} text-white font-semibold shrink-0`}
      style={{ width: size, height: size, fontSize: Math.max(10, size * 0.36) }}
      aria-hidden
    >
      {initialsOf(name)}
    </span>
  );
}

/* ─── Custom node components ─── */

function EngagerNode({ data }: NodeProps<Node<EngagerData>>) {
  const { engager, dim } = data;
  return (
    <div
      className={`bg-card border border-primary/40 rounded-xl px-3 py-2.5 shadow-md transition-opacity ${
        dim ? "opacity-20" : "opacity-100"
      }`}
      style={{ width: NODE_W }}
    >
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <div className="flex items-center gap-2">
        <InlineAvatar
          name={engager.name}
          imageUrl={engager.profile_image_url}
          size={36}
        />
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold leading-tight truncate">
            {engager.name ?? "(unknown)"}
          </div>
          {engager.company && (
            <div className="text-[10px] text-muted-foreground truncate">
              {engager.company}
            </div>
          )}
        </div>
        {engager.stars ? (
          <span className="text-[9px] font-mono text-amber-400 shrink-0">
            {"★".repeat(engager.stars)}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function SourceNode({ data }: NodeProps<Node<SourceData>>) {
  const { source, dim } = data;
  const color = RELEVANCE_COLOR[source.relevance] ?? "border-border/60 bg-card/30";
  return (
    <div
      className={`border rounded-xl px-3 py-2.5 shadow-md transition-opacity ${color} ${
        dim ? "opacity-20" : "opacity-100"
      }`}
      style={{ width: NODE_W }}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <div className="flex items-center gap-2">
        <InlineAvatar
          name={source.name}
          imageUrl={source.profile_image_url}
          size={36}
        />
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold leading-tight truncate">
            {source.name}
          </div>
          <div className="text-[10px] text-muted-foreground truncate">
            {source.relevance}
            {source.tier ? ` · ${source.tier}` : ""}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-1.5 text-[9px] text-muted-foreground">
        <span>{source.engager_count} engagers</span>
        {source.signal_count > 0 && (
          <span className="text-amber-400">· {source.signal_count} signals</span>
        )}
      </div>
    </div>
  );
}

function SignalNode({ data }: NodeProps<Node<SignalData>>) {
  const { signal, dim } = data;
  const color = URGENCY_COLOR[signal.urgency] ?? "border-border/50 bg-card/30";
  return (
    <div
      className={`border rounded-lg px-3 py-2 shadow-md transition-opacity ${color} ${
        dim ? "opacity-20" : "opacity-100"
      }`}
      style={{ width: SIGNAL_NODE_W }}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-0.5">
        {signal.signal_type} · {signal.urgency}
      </div>
      <div className="text-xs font-medium leading-tight line-clamp-2">
        {signal.title}
      </div>
      {signal.post_age_days !== null && (
        <div className="text-[9px] text-muted-foreground mt-1">
          post age {signal.post_age_days}d
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  engager: EngagerNode,
  source: SourceNode,
  signal: SignalNode,
};

/* ─── Dagre layout helper ─── */

function layoutWithDagre(
  nodes: Node<NexusNodeData>[],
  edges: Edge[],
): Node<NexusNodeData>[] {
  const g = new Dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 36, ranksep: 120, ranker: "network-simplex" });

  for (const n of nodes) {
    const isSignal = n.data.kind === "signal";
    g.setNode(n.id, {
      width: isSignal ? SIGNAL_NODE_W : NODE_W,
      height: isSignal ? SIGNAL_NODE_H : NODE_H,
    });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }

  Dagre.layout(g);

  return nodes.map((n) => {
    const isSignal = n.data.kind === "signal";
    const w = isSignal ? SIGNAL_NODE_W : NODE_W;
    const h = isSignal ? SIGNAL_NODE_H : NODE_H;
    const p = g.node(n.id);
    return {
      ...n,
      position: { x: p.x - w / 2, y: p.y - h / 2 },
    };
  });
}

/* ─── Main graph shell ─── */

function GraphInner({ data }: { data: NexusData }) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const { fitView, setCenter } = useReactFlow();

  const { initialNodes, initialEdges, connectionMap } = useMemo(() => {
    // Build a quick connectivity lookup for hover highlighting
    const connected: Record<string, Set<string>> = {};
    const link = (a: string, b: string) => {
      (connected[a] ??= new Set()).add(b);
      (connected[b] ??= new Set()).add(a);
    };
    for (const e of data.edges) link(e.source, e.target);

    const engagerNodes: Node<NexusNodeData>[] = data.engagers.map((e) => ({
      id: `engager-${e.id}`,
      type: "engager",
      position: { x: 0, y: 0 },
      data: { kind: "engager", engager: e, dim: false },
    }));
    const sourceNodes: Node<NexusNodeData>[] = data.sources.map((s) => ({
      id: `source-${s.id}`,
      type: "source",
      position: { x: 0, y: 0 },
      data: { kind: "source", source: s, dim: false },
    }));
    const signalNodes: Node<NexusNodeData>[] = data.signals.map((s) => ({
      id: `signal-${s.id}`,
      type: "signal",
      position: { x: 0, y: 0 },
      data: { kind: "signal", signal: s, dim: false },
    }));

    const rawNodes = [...engagerNodes, ...sourceNodes, ...signalNodes];

    const flowEdges: Edge[] = data.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      animated: e.id.startsWith("s-"),
      style: {
        strokeWidth: Math.min(1 + e.weight * 0.5, 4),
        stroke: e.id.startsWith("s-") ? "var(--accent)" : "var(--muted-foreground)",
        opacity: 0.6,
      },
    }));

    const laidOut = layoutWithDagre(rawNodes, flowEdges);
    return {
      initialNodes: laidOut,
      initialEdges: flowEdges,
      connectionMap: connected,
    };
  }, [data]);

  // Apply hover dimming via node data mutation (xyflow honors data changes)
  const nodes = useMemo(() => {
    if (!hoveredId) return initialNodes;
    const keep = new Set<string>([hoveredId, ...(connectionMap[hoveredId] ?? [])]);
    return initialNodes.map((n) => ({
      ...n,
      data: { ...n.data, dim: !keep.has(n.id) } as NexusNodeData,
    }));
  }, [initialNodes, hoveredId, connectionMap]);

  const edges = useMemo(() => {
    if (!hoveredId) return initialEdges;
    return initialEdges.map((e) => {
      const connected = e.source === hoveredId || e.target === hoveredId;
      return {
        ...e,
        style: {
          ...e.style,
          opacity: connected ? 0.9 : 0.08,
          strokeWidth: connected
            ? Math.max(2, Number(e.style?.strokeWidth ?? 2))
            : Number(e.style?.strokeWidth ?? 1),
        },
      };
    });
  }, [initialEdges, hoveredId]);

  const onNodeMouseEnter = useCallback<NodeMouseHandler>((_, node) => {
    setHoveredId(node.id);
  }, []);
  const onNodeMouseLeave = useCallback<NodeMouseHandler>(() => {
    setHoveredId(null);
  }, []);
  const onNodeClick = useCallback<NodeMouseHandler>(
    (_, node) => {
      setCenter(node.position.x + NODE_W / 2, node.position.y + NODE_H / 2, {
        zoom: 1.4,
        duration: 400,
      });
    },
    [setCenter],
  );

  if (data.engagers.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
        No ICP engagers with source connections yet. Run{" "}
        <code className="mx-1 text-[11px]">scrape_engagers.py</code>
        then{" "}
        <code className="mx-1 text-[11px]">score_icp.py</code>.
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeMouseEnter={onNodeMouseEnter}
      onNodeMouseLeave={onNodeMouseLeave}
      onNodeClick={onNodeClick}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      nodesDraggable
      panOnScroll
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
      onInit={() => {
        // Initial fitView is implicit via the prop; no-op handler keeps a hook
        // point available if we need post-mount focus later.
        setTimeout(() => fitView({ padding: 0.15 }), 0);
      }}
    >
      <Background gap={24} size={1} />
      <Controls showInteractive={false} />
      <MiniMap
        pannable
        zoomable
        className="!bg-card/80 !border !border-border/60"
        nodeColor={(n) => {
          const d = n.data as NexusNodeData;
          if (d.kind === "engager") return "#2563eb";
          if (d.kind === "source") {
            if (d.source.relevance === "competitor") return "#ef4444";
            if (d.source.relevance === "thought-leader") return "#f59e0b";
            if (d.source.relevance === "founder") return "#8b5cf6";
            return "#64748b";
          }
          return "#06b6d4";
        }}
      />
    </ReactFlow>
  );
}

export function SystemNexusGraph({ data }: { data: NexusData }) {
  return (
    <div className="w-full h-full">
      <ReactFlowProvider>
        <GraphInner data={data} />
      </ReactFlowProvider>
    </div>
  );
}
