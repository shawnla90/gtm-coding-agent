"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { platformColors, categoryColors } from "@/lib/format";

type NexusPerson = {
  id: number;
  name: string;
  company: string | null;
  platforms: string[];
  stars: number | null;
};

type NexusAuthor = {
  handle: string;
  name: string | null;
  platform: string;
  shared_posts: number;
};

type NexusTopic = {
  name: string;
  category: string;
  count: number;
};

type NexusCoPerson = {
  id: number;
  name: string | null;
  company: string | null;
  shared_posts: number;
  platforms: string[];
  stars: number | null;
};

type CenterData = { kind: "center"; person: NexusPerson };
type AuthorData = { kind: "author"; author: NexusAuthor };
type TopicData = { kind: "topic"; topic: NexusTopic };
type CoPersonData = { kind: "coperson"; person: NexusCoPerson };

/* ─── Custom node renderers ─── */

function CenterNode({ data }: NodeProps<Node<CenterData>>) {
  const { person } = data;
  return (
    <div className="relative bg-card border-2 border-primary/40 rounded-2xl px-5 py-4 shadow-lg min-w-[180px]">
      <Handle type="source" position={Position.Top} className="!opacity-0" />
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
      <Handle type="source" position={Position.Left} className="!opacity-0" />
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">
        person
      </div>
      <div className="text-sm font-semibold leading-tight">{person.name}</div>
      {person.company && (
        <div className="text-[11px] text-muted-foreground mt-0.5">
          {person.company}
        </div>
      )}
      <div className="flex items-center gap-1.5 mt-2">
        {person.platforms.map((p) => (
          <span
            key={p}
            className="inline-flex items-center justify-center size-5 rounded font-mono text-[10px] font-bold"
            style={{
              backgroundColor: (platformColors[p] ?? "#71717a") + "22",
              color: platformColors[p] ?? "#71717a",
            }}
          >
            {p === "linkedin" ? "in" : p === "x" ? "X" : p[0]}
          </span>
        ))}
        {person.stars ? (
          <span className="text-[10px] font-mono text-amber-400">
            {"★".repeat(person.stars)}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function AuthorNode({ data }: NodeProps<Node<AuthorData>>) {
  const { author } = data;
  const color = platformColors[author.platform] ?? "#71717a";
  return (
    <div
      className="bg-card border rounded-lg px-3 py-2 text-center min-w-[120px]"
      style={{ borderColor: color + "40" }}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <div className="text-[9px] uppercase tracking-wider" style={{ color }}>
        tracked · {author.platform}
      </div>
      <div className="text-[11px] font-medium truncate mt-0.5">
        {author.name ?? author.handle}
      </div>
      <div className="text-[9px] text-muted-foreground">
        {author.shared_posts} shared
      </div>
    </div>
  );
}

function TopicNode({ data }: NodeProps<Node<TopicData>>) {
  const { topic } = data;
  const color = categoryColors[topic.category] ?? "#71717a";
  return (
    <div
      className="bg-card/80 border rounded-full px-3 py-1.5 text-[10px] font-medium"
      style={{ borderColor: color + "60", color }}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      #{topic.name}
      <span className="text-muted-foreground ml-1">({topic.count})</span>
    </div>
  );
}

function CoPersonNode({ data }: NodeProps<Node<CoPersonData>>) {
  const { person } = data;
  return (
    <a
      href={`/people/${person.id}`}
      className="block bg-card border border-border rounded-lg px-3 py-2 hover:border-primary/50 transition-colors min-w-[140px] max-w-[180px]"
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <div className="text-[9px] uppercase tracking-wider text-muted-foreground">
        co-engager · {person.shared_posts}×
      </div>
      <div className="text-[11px] font-medium truncate mt-0.5">
        {person.name ?? "(unknown)"}
      </div>
      {person.company && (
        <div className="text-[9px] text-muted-foreground truncate">
          {person.company}
        </div>
      )}
      <div className="flex items-center gap-1 mt-1">
        {person.platforms.map((p) => (
          <span
            key={p}
            className="inline-flex items-center justify-center size-3.5 rounded font-mono text-[8px] font-bold"
            style={{
              backgroundColor: (platformColors[p] ?? "#71717a") + "22",
              color: platformColors[p] ?? "#71717a",
            }}
          >
            {p === "linkedin" ? "in" : p === "x" ? "X" : p[0]}
          </span>
        ))}
        {person.stars ? (
          <span className="text-[9px] text-amber-400 ml-auto">
            {"★".repeat(person.stars)}
          </span>
        ) : null}
      </div>
    </a>
  );
}

const nodeTypes = {
  center: CenterNode,
  author: AuthorNode,
  topic: TopicNode,
  coperson: CoPersonNode,
};

/* ─── Layout: radial polar coords ─── */

function polar(angleRad: number, radius: number) {
  return { x: radius * Math.cos(angleRad), y: radius * Math.sin(angleRad) };
}

export function NexusGraph({
  person,
  authors,
  topics,
  coPeople,
}: {
  person: NexusPerson;
  authors: NexusAuthor[];
  topics: NexusTopic[];
  coPeople: NexusCoPerson[];
}) {
  const { nodes, edges } = useMemo(() => {
    const centerX = 0;
    const centerY = 0;
    const nodes: Node[] = [
      {
        id: "center",
        type: "center",
        position: { x: centerX, y: centerY },
        data: { kind: "center", person } satisfies CenterData,
      },
    ];
    const edges: Edge[] = [];

    // Ring 1: topics (top half)
    const topicsShown = topics.slice(0, 5);
    const topicRadius = 220;
    const topicStart = -Math.PI * 0.95;
    const topicSpread = Math.PI * 0.9;
    topicsShown.forEach((topic, i) => {
      const t = topicsShown.length === 1 ? 0.5 : i / (topicsShown.length - 1);
      const angle = topicStart + topicSpread * t;
      const pos = polar(angle, topicRadius);
      const id = `topic-${i}`;
      nodes.push({
        id,
        type: "topic",
        position: { x: centerX + pos.x, y: centerY + pos.y },
        data: { kind: "topic", topic } satisfies TopicData,
      });
      edges.push({
        id: `e-${id}`,
        source: "center",
        target: id,
        type: "straight",
        animated: false,
        style: {
          stroke: categoryColors[topic.category] ?? "#52525b",
          strokeWidth: 1,
          opacity: 0.5,
        },
      });
    });

    // Ring 2: tracked authors (right side)
    const authorsShown = authors.slice(0, 5);
    const authorRadius = 260;
    const authorStart = -Math.PI * 0.3;
    const authorSpread = Math.PI * 0.6;
    authorsShown.forEach((author, i) => {
      const t = authorsShown.length === 1 ? 0.5 : i / (authorsShown.length - 1);
      const angle = authorStart + authorSpread * t;
      const pos = polar(angle, authorRadius);
      const id = `author-${i}`;
      nodes.push({
        id,
        type: "author",
        position: { x: centerX + pos.x, y: centerY + pos.y },
        data: { kind: "author", author } satisfies AuthorData,
      });
      edges.push({
        id: `e-${id}`,
        source: "center",
        target: id,
        type: "smoothstep",
        style: {
          stroke: platformColors[author.platform] ?? "#71717a",
          strokeWidth: Math.max(1, Math.min(4, author.shared_posts)),
          opacity: 0.6,
        },
      });
    });

    // Ring 3: co-engagers (bottom half)
    const coShown = coPeople.slice(0, 8);
    const coRadius = 340;
    const coStart = Math.PI * 0.15;
    const coSpread = Math.PI * 0.7;
    coShown.forEach((co, i) => {
      const t = coShown.length === 1 ? 0.5 : i / (coShown.length - 1);
      const angle = coStart + coSpread * t;
      const pos = polar(angle, coRadius);
      const id = `co-${co.id}`;
      nodes.push({
        id,
        type: "coperson",
        position: { x: centerX + pos.x, y: centerY + pos.y },
        data: { kind: "coperson", person: co } satisfies CoPersonData,
      });
      edges.push({
        id: `e-${id}`,
        source: "center",
        target: id,
        type: "smoothstep",
        style: {
          stroke: "#d4a843",
          strokeWidth: Math.max(1, Math.min(3, co.shared_posts)),
          opacity: 0.5,
        },
      });
    });

    return { nodes, edges };
  }, [person, authors, topics, coPeople]);

  return (
    <div className="w-full h-[560px] rounded-xl border border-border/40 bg-background/30 overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag
        zoomOnScroll
      >
        <Background gap={24} color="#ffffff08" />
        <Controls showInteractive={false} className="!bg-card !border-border" />
      </ReactFlow>
    </div>
  );
}
