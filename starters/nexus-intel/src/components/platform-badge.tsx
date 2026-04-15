import type { Platform } from "@/lib/db";

const labelMap: Record<Platform, string> = {
  linkedin: "LI",
  x: "X",
  reddit: "R",
  blog: "B",
  podcast: "P",
  newsletter: "N",
  other: "?",
};

const colorMap: Record<Platform, string> = {
  linkedin: "text-sky-400 border-sky-500/30 bg-sky-500/5",
  x: "text-zinc-200 border-zinc-500/30 bg-zinc-500/5",
  reddit: "text-orange-400 border-orange-500/30 bg-orange-500/5",
  blog: "text-zinc-400 border-zinc-500/30",
  podcast: "text-zinc-400 border-zinc-500/30",
  newsletter: "text-zinc-400 border-zinc-500/30",
  other: "text-zinc-400 border-zinc-500/30",
};

export function PlatformBadge({ platform }: { platform: Platform }) {
  return (
    <span
      className={`inline-flex h-5 min-w-5 items-center justify-center rounded border px-1 text-[9px] font-semibold tracking-wide ${colorMap[platform]}`}
      title={platform}
    >
      {labelMap[platform]}
    </span>
  );
}
