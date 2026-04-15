"use client";

import { motion, useMotionValue, useSpring } from "motion/react";
import type { ReactNode, MouseEvent } from "react";

type Props = {
  children: ReactNode;
  className?: string;
  /** Activation radius in px (default 120) */
  radius?: number;
  /** Pull strength 0–1 (default 0.3) */
  strength?: number;
  /** Spring config */
  springOptions?: { stiffness?: number; damping?: number; mass?: number };
};

export function MagneticButton({
  children,
  className,
  radius = 120,
  strength = 0.3,
  springOptions = { stiffness: 150, damping: 15, mass: 1 },
}: Props) {
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const x = useSpring(rawX, springOptions);
  const y = useSpring(rawY, springOptions);

  function onMouseMove(e: MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const distX = e.clientX - centerX;
    const distY = e.clientY - centerY;
    const dist = Math.sqrt(distX * distX + distY * distY);

    if (dist < radius) {
      const pull = (1 - dist / radius) * strength;
      rawX.set(distX * pull);
      rawY.set(distY * pull);
    } else {
      rawX.set(0);
      rawY.set(0);
    }
  }

  function onMouseLeave() {
    rawX.set(0);
    rawY.set(0);
  }

  return (
    <motion.div
      className={className}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{ x, y }}
    >
      {children}
    </motion.div>
  );
}
