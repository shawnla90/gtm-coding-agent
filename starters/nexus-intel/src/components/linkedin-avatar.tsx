import Image from "next/image";

/**
 * LinkedInAvatar — one component for all person/company faces across the app.
 *
 * Renders a real LinkedIn/X CDN photo via next/image when `imageUrl` is set,
 * falling back to a deterministic gradient-initials circle otherwise.
 *
 * Used on: engager grids, people grids, leader/competitor grids, nexus nodes,
 * SDR brief hero headers. Keep this the single source of truth — don't
 * re-implement initials circles inline.
 *
 * Open risk: LinkedIn CDN URLs can be time-signed. If images 404 after a few
 * days, we need a refresh pass (out of scope for v1 — see pre-launch plan).
 */

type Platform = "linkedin" | "x" | "reddit";

type Size = "xs" | "sm" | "md" | "lg" | "xl";

interface Props {
  name: string | null;
  imageUrl?: string | null;
  size?: Size;
  platform?: Platform;
  className?: string;
}

const SIZE_PX: Record<Size, number> = {
  xs: 20,
  sm: 28,
  md: 36,
  lg: 48,
  xl: 72,
};

const SIZE_TEXT: Record<Size, string> = {
  xs: "text-[8px]",
  sm: "text-[10px]",
  md: "text-xs",
  lg: "text-sm",
  xl: "text-base",
};

const PLATFORM_COLOR: Record<Platform, string> = {
  linkedin: "bg-[#0a66c2]",
  x: "bg-foreground",
  reddit: "bg-[#ff4500]",
};

// 6 gradient palettes — name hash picks one so initials stay stable per person.
const GRADIENTS = [
  "bg-gradient-to-br from-blue-500 to-cyan-500",
  "bg-gradient-to-br from-violet-500 to-purple-500",
  "bg-gradient-to-br from-amber-500 to-rose-500",
  "bg-gradient-to-br from-emerald-500 to-teal-500",
  "bg-gradient-to-br from-pink-500 to-rose-500",
  "bg-gradient-to-br from-indigo-500 to-blue-500",
];

function gradientFor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0;
  return GRADIENTS[Math.abs(h) % GRADIENTS.length];
}

function initialsOf(name: string | null): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export function LinkedInAvatar({
  name,
  imageUrl,
  size = "md",
  platform,
  className = "",
}: Props) {
  const px = SIZE_PX[size];
  const initials = initialsOf(name);
  const gradient = gradientFor(name ?? "?");
  const alt = name ? `${name} profile photo` : "Profile photo";

  const ring = "ring-1 ring-border/60";
  const base = `relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full ${ring} ${className}`;

  return (
    <span
      className={base}
      style={{ width: px, height: px }}
      aria-label={alt}
    >
      {imageUrl ? (
        <Image
          src={imageUrl}
          alt={alt}
          width={px}
          height={px}
          className="h-full w-full object-cover"
          // Lower priority — most avatars are below the fold
          loading="lazy"
        />
      ) : (
        <span
          className={`flex h-full w-full items-center justify-center font-semibold text-white ${gradient} ${SIZE_TEXT[size]}`}
          aria-hidden
        >
          {initials}
        </span>
      )}
      {platform && (
        <span
          className={`absolute -bottom-0.5 -right-0.5 rounded-full ${PLATFORM_COLOR[platform]} ring-2 ring-background`}
          style={{ width: Math.max(6, Math.round(px * 0.22)), height: Math.max(6, Math.round(px * 0.22)) }}
          aria-hidden
        />
      )}
    </span>
  );
}
