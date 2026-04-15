"use client";

import { motion } from "motion/react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

type Props = {
  /** Circle diameter in px (default 400) */
  circleSize?: number;
  /** Circle bg class (default "bg-white/20") */
  circleClassName?: string;
  className?: string;
};

/**
 * ClippedCircle — cursor-following spotlight effect.
 *
 * Place as a direct child of a `relative overflow-hidden` container.
 * Uses mix-blend-mode: difference for a reveal/invert effect.
 * Tracks the cursor position within the parent as a percentage.
 */
export function ClippedCircle({
  circleSize = 400,
  circleClassName = "bg-white/20",
  className,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x: 50, y: 50 });
  const [visible, setVisible] = useState(false);

  function onMouseMove(e: React.MouseEvent) {
    const parent = ref.current?.parentElement;
    if (!parent) return;
    const rect = parent.getBoundingClientRect();
    setPos({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  }

  function onMouseEnter() {
    setVisible(true);
  }

  function onMouseLeave() {
    setVisible(false);
  }

  return (
    <div
      ref={ref}
      className={cn("pointer-events-none absolute inset-0", className)}
      onMouseMove={onMouseMove}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{ pointerEvents: "none", mixBlendMode: "difference" }}
    >
      <motion.div
        className={cn("absolute rounded-full", circleClassName)}
        style={{
          width: circleSize,
          height: circleSize,
          left: `${pos.x}%`,
          top: `${pos.y}%`,
          translateX: "-50%",
          translateY: "-50%",
        }}
        animate={{ scale: visible ? 1 : 0 }}
        transition={{ duration: 0.4, ease: [0.19, 1, 0.22, 1] }}
      />
    </div>
  );
}
