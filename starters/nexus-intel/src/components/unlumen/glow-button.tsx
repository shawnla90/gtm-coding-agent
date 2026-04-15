"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type GlowMode = "rotate" | "pulse" | "breathe";

type Props = {
  children: ReactNode;
  className?: string;
  /** Glow animation mode (default "breathe") */
  mode?: GlowMode;
  /** Gradient colors (default: Apollo teal → pink) */
  colors?: string[];
  /** Blur radius class (default "blur-md") */
  blur?: string;
  /** Animation duration in seconds (default 3) */
  duration?: number;
  /** Scale of glow on hover (default 1.15) */
  glowScale?: number;
};

const defaultColors = ["#D4A843", "#EC4899", "#D4A843"];

function getAnimation(mode: GlowMode, colors: string[], duration: number) {
  switch (mode) {
    case "rotate":
      return {
        background: colors.map(
          (_, i) =>
            `conic-gradient(from ${i * 120}deg, ${colors.join(", ")})`
        ),
        transition: { duration, repeat: Infinity, ease: "linear" as const },
      };
    case "pulse":
      return {
        opacity: [0.5, 1, 0.5],
        scale: [0.95, 1.05, 0.95],
        transition: { duration, repeat: Infinity, ease: "easeInOut" as const },
      };
    case "breathe":
    default:
      return {
        opacity: [0.4, 0.8, 0.4],
        transition: { duration, repeat: Infinity, ease: "easeInOut" as const },
      };
  }
}

export function GlowButton({
  children,
  className,
  mode = "breathe",
  colors = defaultColors,
  blur = "blur-md",
  duration = 3,
  glowScale = 1.15,
}: Props) {
  const gradient = `conic-gradient(from 0deg, ${colors.join(", ")})`;
  const animation = getAnimation(mode, colors, duration);

  return (
    <motion.div
      className={cn("relative inline-flex", className)}
      whileHover={{ scale: glowScale }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      {/* Glow layer */}
      <motion.div
        className={cn(
          "pointer-events-none absolute inset-0 rounded-[inherit]",
          blur
        )}
        style={{ background: gradient }}
        animate={animation}
        aria-hidden
      />
      {/* Content layer */}
      <div className="relative z-10 rounded-[inherit]">{children}</div>
    </motion.div>
  );
}
