"use client";

import { useRef, useEffect, useState, useCallback, type ReactNode } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  forceRadial,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import { select } from "d3-selection";
import { drag } from "d3-drag";
import { zoom, zoomIdentity, type ZoomBehavior } from "d3-zoom";
import "d3-transition";
import { Plus, Minus, Maximize2, RotateCcw, List, PinOff, Target } from "lucide-react";
import { cn } from "@/lib/utils";
import { Eye, EyeOff } from "lucide-react";
import { signalTypeLabels, signalTypeColor, signalTypeNodeColors } from "@/lib/format";
import { LinkedInAvatar } from "@/components/linkedin-avatar";
import type { DrawerTarget } from "@/components/drawers/types";

type TooltipPlatform = "linkedin" | "x" | "reddit";
function toTooltipPlatform(p?: string): TooltipPlatform | undefined {
  return p === "linkedin" || p === "x" || p === "reddit" ? p : undefined;
}

// -----------------------------------------------------------------
// Types
// -----------------------------------------------------------------

export interface NexusNode extends SimulationNodeDatum {
  id: string;
  label: string;
  subtitle?: string;
  type: "signal" | "source" | "engager";
  urgency?: string;
  relevance?: string;
  stars?: number;
  profileUrl?: string;
  profileImageUrl?: string;
  platform?: string;
  title?: string;
  company?: string;
  sourceContentCount?: number;
  sourceSignalCount?: number;
}

interface NexusEdge extends SimulationLinkDatum<NexusNode> {
  id: string;
  weight: number;
}

interface Props {
  nodes: NexusNode[];
  edges: NexusEdge[];
  className?: string;
  onNodeClick?: (target: DrawerTarget) => void;
}

// -----------------------------------------------------------------
// Colors — fully distinct palette, 9 hues spread across the wheel
// -----------------------------------------------------------------

function nodeColor(node: NexusNode): string {
  if (node.type === "signal") {
    // Signals: one distinct hue per type
    return signalTypeColor(node.subtitle);
  }
  if (node.type === "source") {
    // Sources: each relevance gets its own hue family
    switch (node.relevance) {
      case "competitor": return "#EF4444";       // red
      case "thought-leader": return "#F97316";   // orange
      case "founder": return "#A855F7";          // violet
      default: return "#0EA5E9";                 // sky (affiliate/neutral)
    }
  }
  // Engagers: yellow (hero) → pink → slate by star tier
  if (node.stars && node.stars >= 4) return "#FACC15"; // glowing yellow
  if (node.stars && node.stars >= 3) return "#EC4899"; // pink
  return "#94A3B8";                                     // slate (lower ICP)
}

/**
 * Glow rules:
 * - act-now signals pulse with urgency
 * - 4★ engagers always glow (hero role)
 * - All engagers glow when avatars are hidden (helps identify people in color mode)
 */
function shouldGlowNode(node: NexusNode, avatarsHidden: boolean): boolean {
  if (node.type === "signal" && node.urgency === "act-now") return true;
  if (node.type === "engager") {
    if (avatarsHidden) return true;
    return !!node.stars && node.stars >= 4;
  }
  return false;
}

function isHeroNode(node: NexusNode): boolean {
  return node.type === "engager" && !!node.stars && node.stars >= 4;
}

function nodeRadius(node: NexusNode): number {
  if (node.type === "signal") return 8;
  if (node.type === "source") return 12;
  return 6 + (node.stars ?? 0);
}

// -----------------------------------------------------------------
// Component
// -----------------------------------------------------------------

export function ForceNexus({
  nodes,
  edges,
  className,
  onNodeClick,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 900, height: 700 });
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showAvatars, setShowAvatars] = useState(true);
  const [showRoleRing, setShowRoleRing] = useState(true);
  const [guideCollapsed, setGuideCollapsed] = useState(false);
  const prevAvatarsRef = useRef(true);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const simulationRef = useRef<ReturnType<typeof forceSimulation<NexusNode>> | null>(null);
  const driftRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  // Track connected nodes for hover highlighting
  const connectedMap = useRef<Map<string, Set<string>>>(new Map());

  useEffect(() => {
    const map = new Map<string, Set<string>>();
    for (const edge of edges) {
      const src = typeof edge.source === "string" ? edge.source : (edge.source as NexusNode).id;
      const tgt = typeof edge.target === "string" ? edge.target : (edge.target as NexusNode).id;
      if (!map.has(src)) map.set(src, new Set());
      if (!map.has(tgt)) map.set(tgt, new Set());
      map.get(src)!.add(tgt);
      map.get(tgt)!.add(src);
    }
    connectedMap.current = map;
  }, [edges]);

  // Responsive
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setDimensions({ width, height });
      }
    });
    ro.observe(svg.parentElement!);
    return () => ro.disconnect();
  }, []);

  // Legend always defaults to open. Auto-collapsing on mount was causing a
  // brief flash-then-hide on narrow viewports (including desktops with wide
  // devtools panels). User can toggle manually. One-time cleanup of the old
  // localStorage key so stale "collapsed=true" from prior builds can't leak.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem("apollo-nexus-guide-collapsed");
    } catch {
      // noop
    }
  }, []);

  // Cleanup tooltip timer on unmount
  useEffect(() => {
    return () => {
      if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    };
  }, []);

  const toggleGuide = useCallback(() => {
    setGuideCollapsed((prev) => !prev);
  }, []);

  // Zoom + Pan — attached once, persists across simulation remounts
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .filter((event) => {
        // Wheel always zooms (even over nodes)
        if (event.type === "wheel") return true;
        // Pointer drags starting on a node → fall through to d3-drag
        const target = event.target as Element | null;
        if (target?.closest?.("g.node")) return false;
        // Default: no ctrl, primary button only
        return !event.ctrlKey && !event.button;
      })
      .on("zoom", (event) => {
        select(svg)
          .select<SVGGElement>("g.zoom-container")
          .attr("transform", event.transform.toString());
      });

    select(svg).call(zoomBehavior);
    zoomRef.current = zoomBehavior;

    return () => {
      select(svg).on(".zoom", null);
    };
  }, []);

  // Compute bbox of simulation nodes → returns transform to fit viewport
  const computeFitTransform = useCallback(() => {
    const sim = simulationRef.current;
    if (!sim) return null;
    const simNodes = sim.nodes();
    let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
    for (const n of simNodes) {
      if (n.x == null || n.y == null) continue;
      xMin = Math.min(xMin, n.x);
      xMax = Math.max(xMax, n.x);
      yMin = Math.min(yMin, n.y);
      yMax = Math.max(yMax, n.y);
    }
    if (!isFinite(xMin)) return null;
    const { width, height } = dimensions;
    const pad = 80;
    const w = xMax - xMin + pad * 2;
    const h = yMax - yMin + pad * 2;
    const scale = Math.min(width / w, height / h, 1);
    const tx = width / 2 - scale * (xMin + xMax) / 2;
    const ty = height / 2 - scale * (yMin + yMax) / 2;
    return zoomIdentity.translate(tx, ty).scale(scale);
  }, [dimensions]);

  const zoomBy = useCallback((factor: number) => {
    const svg = svgRef.current;
    const zoomB = zoomRef.current;
    if (!svg || !zoomB) return;
    select(svg).transition().duration(250).call(zoomB.scaleBy, factor);
  }, []);

  const resetZoom = useCallback(() => {
    const svg = svgRef.current;
    const zoomB = zoomRef.current;
    if (!svg || !zoomB) return;
    select(svg).transition().duration(400).call(zoomB.transform, zoomIdentity);
  }, []);

  const releaseAllPins = useCallback(() => {
    const sim = simulationRef.current;
    if (!sim) return;
    sim.nodes().forEach((n) => {
      n.fx = null;
      n.fy = null;
    });
    sim.alpha(0.4).restart();
    const svg = svgRef.current;
    if (svg) {
      select(svg).selectAll<SVGCircleElement, NexusNode>("circle.pin-ring").attr("opacity", 0);
    }
  }, []);

  const fitToViewport = useCallback(() => {
    const svg = svgRef.current;
    const zoomB = zoomRef.current;
    if (!svg || !zoomB) return;
    const t = computeFitTransform();
    if (!t) return;
    select(svg).transition().duration(400).call(zoomB.transform, t);
  }, [computeFitTransform]);

  // Force simulation
  useEffect(() => {
    if (!nodes.length) return;

    const { width, height } = dimensions;
    const cx = width / 2;
    const cy = height / 2;
    const minDim = Math.min(width, height);

    // Clone nodes to avoid mutating props
    const simNodes = nodes.map((n) => ({ ...n }));
    const simEdges = edges.map((e) => ({
      ...e,
      source: typeof e.source === "string" ? e.source : (e.source as NexusNode).id,
      target: typeof e.target === "string" ? e.target : (e.target as NexusNode).id,
    }));

    const simulation = forceSimulation<NexusNode>(simNodes)
      // Balanced damping: still elastic, but settles to a calm drift
      .velocityDecay(0.38)
      // Slightly slower alpha decay than default = lingering motion latency
      .alphaDecay(0.02)
      .force("center", forceCenter(cx, cy).strength(0.04))
      // Much stronger repulsion spreads the strands out — declusters the graph
      .force("charge", forceManyBody().strength(-220))
      .force("collide", forceCollide<NexusNode>((d) => nodeRadius(d) + (showAvatars && d.type === "engager" ? 16 : 14)))
      .force(
        "link",
        forceLink<NexusNode, NexusEdge>(simEdges)
          .id((d) => d.id)
          // Longer strands + moderate pull = room to breathe with visible magnetism
          .distance(160)
          .strength(0.45),
      )
      // Concentric rings
      .force(
        "radial-signal",
        forceRadial<NexusNode>(
          minDim * 0.18,
          cx,
          cy
        ).strength((d) => (d.type === "signal" ? 0.8 : 0))
      )
      .force(
        "radial-source",
        forceRadial<NexusNode>(
          minDim * 0.32,
          cx,
          cy
        ).strength((d) => (d.type === "source" ? 0.6 : 0))
      )
      .force(
        "radial-engager",
        forceRadial<NexusNode>(
          minDim * 0.44,
          cx,
          cy
        ).strength((d) => (d.type === "engager" ? 0.4 : 0))
      );

    simulationRef.current = simulation;

    const svg = select(svgRef.current!);

    // Ring radii for labels
    const ringRadii = [
      { r: minDim * 0.18, label: "Signals" },
      { r: minDim * 0.32, label: "Sources" },
      { r: minDim * 0.44, label: "People" },
    ];

    // Concentric ring guides
    const ringSel = svg
      .select<SVGGElement>(".rings")
      .selectAll<SVGCircleElement, (typeof ringRadii)[0]>("circle")
      .data(ringRadii, (d) => d.label)
      .join("circle")
      .attr("cx", cx)
      .attr("cy", cy)
      .attr("r", (d) => d.r)
      .attr("fill", "none")
      .attr("stroke", "currentColor")
      .attr("stroke-opacity", 0.06)
      .attr("stroke-width", 1)
      .attr("vector-effect", "non-scaling-stroke")
      .attr("stroke-dasharray", "4 6");

    // Ring labels
    const ringLabelSel = svg
      .select<SVGGElement>(".rings")
      .selectAll<SVGTextElement, (typeof ringRadii)[0]>("text")
      .data(ringRadii, (d) => d.label)
      .join("text")
      .attr("x", cx)
      .attr("y", (d) => cy - d.r - 6)
      .attr("text-anchor", "middle")
      .attr("fill", "currentColor")
      .attr("fill-opacity", 0.15)
      .attr("font-size", 10)
      .attr("font-weight", 500)
      .text((d) => d.label);

    // Edges
    const linkSel = svg
      .select<SVGGElement>(".links")
      .selectAll<SVGLineElement, NexusEdge>("line")
      .data(simEdges, (d) => d.id)
      .join("line")
      .attr("stroke", "currentColor")
      .attr("stroke-opacity", 0.15)
      .attr("stroke-width", (d) => Math.max(1, d.weight * 0.5))
      .attr("vector-effect", "non-scaling-stroke");

    // Animated pulse on source→signal edges
    linkSel
      .filter((d) => {
        const src = typeof d.source === "string" ? d.source : (d.source as NexusNode).id;
        return src.startsWith("source-");
      })
      .attr("stroke-dasharray", "6 4")
      .each(function () {
        const el = select(this);
        function animateDash() {
          el.attr("stroke-dashoffset", 0)
            .transition()
            .duration(3000)
            .ease((t: number) => t) // linear
            .attr("stroke-dashoffset", -30)
            .on("end", animateDash);
        }
        animateDash();
      });

    // Node group — we use <g> elements instead of plain circles for avatar support
    const nodeGroup = svg
      .select<SVGGElement>(".nodes")
      .selectAll<SVGGElement, NexusNode>("g.node")
      .data(simNodes, (d) => d.id)
      .join(
        (enter) => {
          const g = enter.append("g").attr("class", "node");
          // Circle (always present)
          g.append("circle")
            .attr("r", (d) => nodeRadius(d))
            .attr("fill", (d) => nodeColor(d))
            .attr("stroke", (d) => (isHeroNode(d) ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.4)"))
            .attr("stroke-width", (d) => (isHeroNode(d) ? 1.5 : 1))
            .attr("vector-effect", "non-scaling-stroke");
          // Pin indicator (shown when node.fx != null)
          g.append("circle")
            .attr("class", "pin-ring")
            .attr("r", (d) => nodeRadius(d) + 4)
            .attr("fill", "none")
            .attr("stroke", "rgba(255,255,255,0.75)")
            .attr("stroke-dasharray", "2 2")
            .attr("stroke-width", 1)
            .attr("vector-effect", "non-scaling-stroke")
            .attr("opacity", (d) => (d.fx != null ? 1 : 0))
            .style("pointer-events", "none");

          // Clip path for images (engagers + sources both use logos/avatars)
          g.filter((d) => d.type === "engager" || d.type === "source")
            .append("clipPath")
            .attr("id", (d) => `clip-${d.id}`)
            .append("circle")
            .attr("r", (d) => nodeRadius(d) - 1);

          // Image element — only attached if a profileImageUrl exists
          g.filter((d) => (d.type === "engager" || d.type === "source") && !!d.profileImageUrl)
            .append("image")
            .attr("class", "avatar-img")
            .attr("href", (d) => d.profileImageUrl!)
            .attr("x", (d) => -(nodeRadius(d) - 1))
            .attr("y", (d) => -(nodeRadius(d) - 1))
            .attr("width", (d) => (nodeRadius(d) - 1) * 2)
            .attr("height", (d) => (nodeRadius(d) - 1) * 2)
            .attr("clip-path", (d) => `url(#clip-${d.id})`)
            .attr("display", showAvatars ? "block" : "none");

          // Role indicator ring — colored outline around avatar showing what the node IS
          g.filter((d) => d.type === "engager" || d.type === "source")
            .append("circle")
            .attr("class", "role-ring")
            .attr("r", (d) => nodeRadius(d) + 2.5)
            .attr("fill", "none")
            .attr("stroke", (d) => nodeColor(d))
            .attr("stroke-width", 2.5)
            .attr("vector-effect", "non-scaling-stroke")
            .attr("opacity", 0)
            .style("pointer-events", "none");

          return g;
        },
        (update) => update,
        (exit) => exit.remove(),
      );

    // Update avatar visibility
    svg.selectAll<SVGImageElement, NexusNode>("image.avatar-img")
      .attr("display", showAvatars ? "block" : "none");
    // When avatars are shown, hide the base circle fill for any node with an image
    // (The circle underneath still drives glow + fallback color when image missing.)
    nodeGroup.select<SVGCircleElement>("circle:not(.pin-ring):not(.role-ring)")
      .attr("fill-opacity", (d) =>
        showAvatars && (d.type === "engager" || d.type === "source") && d.profileImageUrl ? 0 : 1
      )
      .attr("filter", (d) =>
        shouldGlowNode(d, !showAvatars) ? "url(#nexus-glow)" : null,
      );
    // Role ring — only visible when avatars are shown AND user enabled indicator
    nodeGroup.select<SVGCircleElement>("circle.role-ring")
      .attr("opacity", (d) =>
        showAvatars && showRoleRing && d.profileImageUrl ? 1 : 0,
      );

    nodeGroup.style("cursor", () => (onNodeClick ? "pointer" : "grab"));

    // Drag behavior — release LEAVES the node pinned at its drop position.
    // Shift+click on a pinned node unpins it (see click handler below).
    const dragBehavior = drag<SVGGElement, NexusNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        // Keep fx/fy set so the node stays pinned where you dropped it.
        // Flash the pin indicator on for this node.
        void d;
        nodeGroup.select<SVGCircleElement>("circle.pin-ring").attr("opacity", (n) =>
          n.fx != null ? 1 : 0,
        );
      });

    nodeGroup.call(dragBehavior);

    // Click handler — shift-click unpins, plain click opens drawer
    nodeGroup.on("click", (event: MouseEvent, d) => {
      if (event.shiftKey) {
        d.fx = null;
        d.fy = null;
        if (!simulation) return;
        simulation.alpha(0.3).restart();
        // Refresh pin indicator
        nodeGroup.select<SVGCircleElement>("circle.pin-ring").attr("opacity", (n) =>
          n.fx != null ? 1 : 0,
        );
        return;
      }
      if (!onNodeClick) return;
      const idNum = parseInt(d.id.replace(/^(signal|source|engager)-/, ""), 10);
      if (Number.isNaN(idNum)) return;
      onNodeClick({ type: d.type, id: idNum });
    });

    // Hover — sets dim-state immediately, tooltip pos after 100ms debounce
    nodeGroup
      .on("mouseenter", (event: MouseEvent, d) => {
        setHoveredId(d.id);
        const container = svgRef.current?.parentElement;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
        tooltipTimerRef.current = setTimeout(() => {
          setTooltipPos({ x, y });
        }, 100);
      })
      .on("mouseleave", () => {
        setHoveredId(null);
        if (tooltipTimerRef.current) {
          clearTimeout(tooltipTimerRef.current);
          tooltipTimerRef.current = null;
        }
        setTooltipPos(null);
      });

    // Tick
    simulation.on("tick", () => {
      linkSel
        .attr("x1", (d) => (d.source as unknown as NexusNode).x ?? 0)
        .attr("y1", (d) => (d.source as unknown as NexusNode).y ?? 0)
        .attr("x2", (d) => (d.target as unknown as NexusNode).x ?? 0)
        .attr("y2", (d) => (d.target as unknown as NexusNode).y ?? 0);

      nodeGroup.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    // Ambient drift — gentle, periodic reheat so the graph keeps breathing
    if (driftRef.current) clearInterval(driftRef.current);
    driftRef.current = setInterval(() => {
      if (simulation.alpha() < 0.025) {
        simulation.alpha(0.04).restart();
      }
    }, 6000);

    // Fit to viewport once simulation settles
    const fitTimer = setTimeout(() => {
      const svgEl = svgRef.current;
      const zoomB = zoomRef.current;
      if (!svgEl || !zoomB) return;
      const t = computeFitTransform();
      if (!t) return;
      select(svgEl).transition().duration(400).call(zoomB.transform, t);
    }, 400);

    return () => {
      simulation.stop();
      if (driftRef.current) clearInterval(driftRef.current);
      clearTimeout(fitTimer);
    };
  }, [nodes, edges, dimensions, showAvatars, showRoleRing, onNodeClick, computeFitTransform]);

  // When user hides avatars, auto-open the legend so color meaning is instantly visible
  useEffect(() => {
    if (prevAvatarsRef.current && !showAvatars) {
      setGuideCollapsed(false);
    }
    prevAvatarsRef.current = showAvatars;
  }, [showAvatars]);

  // Hover highlighting via opacity
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const s = select(svg);
    if (!hoveredId) {
      s.selectAll("g.node").attr("opacity", 1);
      s.selectAll(".links line").attr("stroke-opacity", 0.15);
      return;
    }

    const connected = connectedMap.current.get(hoveredId) ?? new Set();
    s.selectAll<SVGGElement, NexusNode>("g.node").attr("opacity", (d) =>
      d.id === hoveredId || connected.has(d.id) ? 1 : 0.15
    );
    s.selectAll<SVGLineElement, NexusEdge>(".links line").attr("stroke-opacity", (d) => {
      const src = typeof d.source === "string" ? d.source : (d.source as NexusNode).id;
      const tgt = typeof d.target === "string" ? d.target : (d.target as NexusNode).id;
      if (src === hoveredId || tgt === hoveredId) return 0.6;
      return 0.04;
    }).attr("stroke", (d) => {
      const src = typeof d.source === "string" ? d.source : (d.source as NexusNode).id;
      const tgt = typeof d.target === "string" ? d.target : (d.target as NexusNode).id;
      if (src === hoveredId || tgt === hoveredId) return "#D4A843";
      return "currentColor";
    });
  }, [hoveredId]);

  return (
    <div className={cn("relative w-full h-full min-h-[500px]", className)}>
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="w-full h-full touch-none"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
      >
        <defs>
          <filter id="nexus-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4.5" result="blur1" />
            <feGaussianBlur stdDeviation="1.5" in="SourceGraphic" result="blur2" />
            <feMerge>
              <feMergeNode in="blur1" />
              <feMergeNode in="blur2" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g className="zoom-container">
          <g className="rings" />
          <g className="links" />
          <g className="nodes" />
        </g>
      </svg>

      {/* Visibility toggles */}
      <div className="absolute top-4 right-4 flex items-center gap-1.5">
        <ToggleChip
          active={!guideCollapsed}
          onClick={toggleGuide}
          icon={<List className="h-3 w-3" />}
          label="Legend"
        />
        <ToggleChip
          active={showAvatars && showRoleRing}
          disabled={!showAvatars}
          onClick={() => setShowRoleRing((v) => !v)}
          icon={<Target className="h-3 w-3" />}
          label="Role ring"
        />
        <ToggleChip
          active={showAvatars}
          onClick={() => setShowAvatars((v) => !v)}
          icon={showAvatars ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
          label="Avatars"
        />
      </div>

      {/* Zoom + pin controls */}
      <div className="absolute top-14 right-4 flex flex-col gap-1">
        <ZoomButton title="Zoom in" onClick={() => zoomBy(1.3)}>
          <Plus className="h-3.5 w-3.5" />
        </ZoomButton>
        <ZoomButton title="Zoom out" onClick={() => zoomBy(1 / 1.3)}>
          <Minus className="h-3.5 w-3.5" />
        </ZoomButton>
        <ZoomButton title="Fit to view" onClick={fitToViewport}>
          <Maximize2 className="h-3.5 w-3.5" />
        </ZoomButton>
        <ZoomButton title="Reset zoom" onClick={resetZoom}>
          <RotateCcw className="h-3.5 w-3.5" />
        </ZoomButton>
        <ZoomButton title="Release pinned nodes" onClick={releaseAllPins}>
          <PinOff className="h-3.5 w-3.5" />
        </ZoomButton>
      </div>

      {/* Hover tooltip */}
      {hoveredId && tooltipPos && (() => {
        const node = nodes.find((n) => n.id === hoveredId);
        if (!node) return null;
        const isSignal = node.type === "signal";
        const TOOLTIP_W = isSignal ? 240 : 280;
        const TOOLTIP_H = isSignal ? 60 : 76;
        const left = Math.min(tooltipPos.x + 12, dimensions.width - TOOLTIP_W - 8);
        const top = Math.min(tooltipPos.y + 12, dimensions.height - TOOLTIP_H - 8);
        return (
          <div
            className="pointer-events-none absolute z-10 rounded-md border border-border/50 bg-card/95 px-2.5 py-2 text-[10px] shadow-lg backdrop-blur-sm animate-in fade-in-0 duration-150"
            style={{ left, top, maxWidth: TOOLTIP_W }}
          >
            {isSignal && (
              <>
                <div className="flex items-center gap-1.5 font-medium text-foreground">
                  <span>{signalTypeLabels[node.subtitle ?? ""] ?? "Signal"}</span>
                  {node.urgency && (
                    <span className="text-muted-foreground">· {node.urgency}</span>
                  )}
                </div>
                <div className="truncate text-muted-foreground">{node.label}</div>
              </>
            )}
            {node.type === "source" && (
              <div className="flex items-center gap-2.5">
                <LinkedInAvatar
                  name={node.label}
                  imageUrl={node.profileImageUrl}
                  platform={toTooltipPlatform(node.platform)}
                  size="md"
                />
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-foreground">
                    {relevanceDisplay(node.relevance)}
                  </div>
                  <div className="truncate text-muted-foreground">{node.label}</div>
                  {node.platform && (
                    <div className="truncate text-[9px] uppercase tracking-wide text-muted-foreground/70">
                      {node.platform}
                    </div>
                  )}
                </div>
              </div>
            )}
            {node.type === "engager" && (
              <div className="flex items-center gap-2.5">
                <LinkedInAvatar
                  name={node.label}
                  imageUrl={node.profileImageUrl}
                  platform={toTooltipPlatform(node.platform)}
                  size="md"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 font-medium text-foreground">
                    <span className="truncate">{node.label}</span>
                    {node.stars != null && node.stars > 0 && (
                      <span className="shrink-0 text-primary">{node.stars}★</span>
                    )}
                  </div>
                  <div className="truncate text-muted-foreground">
                    {node.title ?? node.company ?? ""}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Bottom explanation panel — z-30 + solid bg + conditional render so no
          stacking or animation quirk can hide it. Slide-up animation via
          Tailwind's animate-in utilities (only runs on mount of the panel). */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-30 flex flex-col">
        {!guideCollapsed && (
          <div className="pointer-events-auto border-t border-border/40 bg-card shadow-lg">
            <div className="flex flex-col gap-2 px-4 pt-3 pb-2 text-[11px]">
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[10px]">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">Rings</span>
                  <span className="text-muted-foreground">
                    inner = signals · middle = sources · outer = people
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">Edges</span>
                  <span className="text-muted-foreground">
                    thickness = engagement · dashed = signal origin
                  </span>
                </div>
                <span className="ml-auto text-muted-foreground">
                  click · scroll · drag · shift-click to unpin
                </span>
              </div>
              <LegendRow title="Signals">
                {Object.entries(signalTypeNodeColors).map(([key, color]) => (
                  <LegendDot
                    key={key}
                    color={color}
                    label={signalTypeLabels[key] ?? key}
                  />
                ))}
              </LegendRow>
              <LegendRow title="Sources">
                <LegendDot color="#EF4444" label="Competitor" />
                <LegendDot color="#F97316" label="Leader" />
                <LegendDot color="#A855F7" label="Founder" />
                <LegendDot color="#0EA5E9" label="Affiliate" />
              </LegendRow>
              <LegendRow title="People">
                <LegendDot color="#FACC15" label="ICP 4★+" glow />
                <LegendDot color="#EC4899" label="ICP 3★" />
                <LegendDot color="#94A3B8" label="Lower ICP" />
              </LegendRow>
            </div>
          </div>
        )}
        <div className="pointer-events-auto flex justify-end border-t border-border/30 bg-card/90 px-4 py-1.5 backdrop-blur-sm">
          <button
            type="button"
            onClick={toggleGuide}
            className="text-[10px] font-medium text-muted-foreground transition-colors hover:text-foreground"
            aria-expanded={!guideCollapsed}
          >
            {guideCollapsed ? "▲ Show legend" : "▼ Hide legend"}
          </button>
        </div>
      </div>
    </div>
  );
}

const RELEVANCE_LABELS: Record<string, string> = {
  competitor: "Competitor",
  "thought-leader": "Thought Leader",
  founder: "Founder",
  other: "Source",
};

function relevanceDisplay(relevance?: string): string {
  if (!relevance) return "Source";
  return RELEVANCE_LABELS[relevance] ?? relevance;
}

function LegendDot({ color, label, glow }: { color: string; label: string; glow?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className="h-2.5 w-2.5 rounded-full"
        style={{
          backgroundColor: color,
          boxShadow: glow ? `0 0 6px ${color}` : undefined,
        }}
      />
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}

function LegendRow({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="w-14 shrink-0 font-medium text-foreground/70">{title}</span>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">{children}</div>
    </div>
  );
}

function ToggleChip({
  active,
  disabled,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={cn(
        "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-medium backdrop-blur-sm transition-colors",
        active
          ? "border-primary/60 bg-primary/15 text-primary"
          : "border-border/50 bg-card/80 text-muted-foreground hover:text-foreground hover:border-primary/30",
        disabled && "cursor-not-allowed opacity-40",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function ZoomButton({
  children,
  onClick,
  title,
}: {
  children: ReactNode;
  onClick: () => void;
  title: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      className="flex h-7 w-7 items-center justify-center rounded-md border border-border/50 bg-card/80 text-muted-foreground backdrop-blur-sm transition-colors hover:text-foreground hover:border-primary/30"
    >
      {children}
    </button>
  );
}
