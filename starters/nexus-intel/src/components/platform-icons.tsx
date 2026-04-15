import { ExternalLink } from "lucide-react";
import { platformColors } from "@/lib/format";

type MiniEngager = {
  platform: string;
  handle: string;
  profile_url: string | null;
};

const PLATFORM_LABEL: Record<string, string> = {
  linkedin: "in",
  x: "X",
  reddit: "r",
};

/**
 * Compact cross-platform identity badges for a person/engager.
 * Pass the set of engager rows that belong to the same person — one icon per
 * distinct platform. Each icon is a link to the external profile, opening in
 * a new tab.
 */
export function PlatformIcons({
  engagers,
  size = "sm",
}: {
  engagers: MiniEngager[];
  size?: "sm" | "md";
}) {
  // Dedupe by platform, preferring the row that has a profile_url
  const byPlatform = new Map<string, MiniEngager>();
  for (const e of engagers) {
    const existing = byPlatform.get(e.platform);
    if (!existing || (!existing.profile_url && e.profile_url)) {
      byPlatform.set(e.platform, e);
    }
  }

  if (byPlatform.size === 0) return null;

  const px = size === "md" ? "px-1.5 h-5 text-[10px]" : "px-1 h-4 text-[9px]";
  const iconSize = size === "md" ? "size-2.5" : "size-2";

  return (
    <div className="flex items-center gap-1">
      {Array.from(byPlatform.values()).map((e) => {
        const color = platformColors[e.platform] ?? "#71717a";
        const url =
          e.profile_url ||
          (e.platform === "x"
            ? `https://x.com/${e.handle}`
            : e.platform === "linkedin"
              ? `https://www.linkedin.com/in/${e.handle}`
              : undefined);
        const label = PLATFORM_LABEL[e.platform] ?? e.platform[0]?.toUpperCase();

        const pill = (
          <span
            className={`inline-flex items-center gap-0.5 rounded border font-mono font-semibold ${px}`}
            style={{
              borderColor: color + "40",
              color,
              backgroundColor: color + "0d",
            }}
          >
            {label}
            {url ? <ExternalLink className={iconSize} /> : null}
          </span>
        );

        return url ? (
          <a
            key={e.platform}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:opacity-80 transition-opacity"
            title={`@${e.handle} on ${e.platform}`}
          >
            {pill}
          </a>
        ) : (
          <span key={e.platform} title={`@${e.handle} on ${e.platform}`}>
            {pill}
          </span>
        );
      })}
    </div>
  );
}
