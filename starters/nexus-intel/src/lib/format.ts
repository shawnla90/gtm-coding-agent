export function truncate(str: string | null, len: number) {
  if (!str) return "";
  return str.length > len ? str.slice(0, len) + "..." : str;
}

export function formatNum(n: number | null) {
  if (!n) return "0";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

export function formatDate(d: string | null) {
  if (!d) return "---";
  const date = new Date(d);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso.replace(" ", "T") + (iso.includes("Z") ? "" : "Z"));
  const diffSec = Math.floor((Date.now() - then.getTime()) / 1000);
  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)}d ago`;
  return then.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function toSlug(str: string) {
  return str.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
}

export const platformIcons: Record<string, string> = {
  x: "X",
  linkedin: "in",
  reddit: "r/",
};

export const platformLabels: Record<string, string> = {
  x: "X / Twitter",
  linkedin: "LinkedIn",
  reddit: "Reddit",
};

export const platformColors: Record<string, string> = {
  x: "#1da1f2",
  linkedin: "#0a66c2",
  reddit: "#ff4500",
};

// Apollo sales-intel topic categories
export const categoryColors: Record<string, string> = {
  "sales-intelligence": "#D4A843",
  "gtm-engineering": "#3B82F6",
  "outbound-strategy": "#F43F5E",
  "ai-sales-tools": "#8B5CF6",
  "data-enrichment": "#D4A843",
  "revenue-ops": "#06B6D4",
  "competitor-intel": "#EF4444",
};

export const categoryLabels: Record<string, string> = {
  "sales-intelligence": "Sales Intelligence",
  "gtm-engineering": "GTM Engineering",
  "outbound-strategy": "Outbound Strategy",
  "ai-sales-tools": "AI Sales Tools",
  "data-enrichment": "Data Enrichment",
  "revenue-ops": "Revenue Ops",
  "competitor-intel": "Competitor Intel",
};

export const urgencyColors: Record<string, string> = {
  "act-now": "bg-red-500/10 text-red-500 border-red-500/20",
  "this-week": "bg-orange-500/10 text-orange-500 border-orange-500/20",
  "this-month": "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  backlog: "bg-zinc-500/10 text-zinc-500 border-zinc-500/20",
};

export const signalTypeColors: Record<string, string> = {
  "content-angle": "bg-amber-500/10 text-amber-400 border-amber-500/20",
  "engagement-hook": "bg-blue-500/10 text-blue-400 border-blue-500/20",
  "audience-pain-point": "bg-rose-500/10 text-rose-400 border-rose-500/20",
  positioning: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  vulnerability: "bg-red-500/10 text-red-400 border-red-500/20",
  trend: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  "product-launch": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  opportunity: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  "content-gap": "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  partnership: "bg-orange-500/10 text-orange-400 border-orange-500/20",
};

/** SVG-safe hex colors for nexus signal nodes — one distinct hue per type. */
export const signalTypeNodeColors: Record<string, string> = {
  positioning: "#8B5CF6",          // violet
  "content-angle": "#F59E0B",      // amber
  trend: "#22D3EE",                // cyan
  "product-launch": "#10B981",     // emerald
  "engagement-hook": "#FB7185",    // coral
  "audience-pain-point": "#F43F5E",// rose
  vulnerability: "#DC2626",        // deep red
  "content-gap": "#84CC16",        // lime
  partnership: "#6366F1",          // indigo
  opportunity: "#14B8A6",          // teal
};

export function signalTypeColor(signalType?: string): string {
  if (!signalType) return "#94A3B8"; // slate fallback
  return signalTypeNodeColors[signalType] ?? "#94A3B8";
}

export const signalTypeLabels: Record<string, string> = {
  "content-angle": "Content Opportunity",
  "engagement-hook": "Engagement Pattern",
  "audience-pain-point": "Buyer Pain Point",
  positioning: "Positioning Shift",
  vulnerability: "Competitive Gap",
  trend: "Market Trend",
  "product-launch": "Product Launch",
  opportunity: "Market Opportunity",
  "content-gap": "Content Gap",
  partnership: "Partnership Move",
};

/** SDR-framed outreach angle per signal type */
export const signalTypeSdrAngles: Record<string, string> = {
  "content-angle": "Their audience engages with this angle — lead with it in outreach",
  "engagement-hook": "This format drives response — mirror it in your messaging",
  "audience-pain-point": "Prospects are struggling with this — open the conversation here",
  positioning: "Competitor repositioned — exploit the gap before they fill it",
  vulnerability: "Weakness spotted — time-sensitive opening for displacement",
  trend: "Rising topic — early movers get mindshare, act now",
  "product-launch": "New product in market — displaced buyers need alternatives",
  opportunity: "Market gap identified — position your solution here",
  "content-gap": "Nobody is covering this yet — first-mover advantage",
  partnership: "Integration/acquisition — affected buyers need alternatives",
};

export const tierColors: Record<string, string> = {
  "tier-1": "bg-red-500/10 text-red-500 border-red-500/30",
  "tier-2": "bg-orange-500/10 text-orange-500 border-orange-500/30",
  adjacent: "bg-amber-500/10 text-amber-500 border-amber-500/30",
  global: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
};
