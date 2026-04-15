"use client";

import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import type { ReactNode, MouseEvent } from "react";

/**
 * TiltCard — subtle 3D tilt on mouse move.
 *
 * Wraps any block element and applies a gentle perspective transform based on
 * cursor position. Used on the home KPI hero strip to pull the eye — not on
 * grid items (would be visually noisy at scale).
 *
 * Usage:
 *   <TiltCard>
 *     <KpiCard ... />
 *   </TiltCard>
 */

type Props = {
  children: ReactNode;
  className?: string;
  /** Max tilt in degrees (default 6) */
  maxTilt?: number;
};

export function TiltCard({ children, className, maxTilt = 6 }: Props) {
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);

  const springRx = useSpring(rx, { stiffness: 200, damping: 20 });
  const springRy = useSpring(ry, { stiffness: 200, damping: 20 });

  const rotateX = useTransform(springRx, (v) => `${v}deg`);
  const rotateY = useTransform(springRy, (v) => `${v}deg`);

  function onMouseMove(e: MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width; // 0..1
    const y = (e.clientY - rect.top) / rect.height; // 0..1
    rx.set((0.5 - y) * maxTilt * 2);
    ry.set((x - 0.5) * maxTilt * 2);
  }

  function onMouseLeave() {
    rx.set(0);
    ry.set(0);
  }

  return (
    <motion.div
      className={className}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{
        rotateX,
        rotateY,
        transformPerspective: 800,
        transformStyle: "preserve-3d",
      }}
    >
      {children}
    </motion.div>
  );
}
