"use client";

import {
  motion,
  useMotionValue,
  useSpring,
  useVelocity,
  useTransform,
  type MotionValue,
} from "motion/react";
import { useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type HighlightItem = {
  id: string;
  label: string;
  href?: string;
  icon?: ReactNode;
};

type Props = {
  items: HighlightItem[];
  activeId: string;
  onSelect: (id: string) => void;
  className?: string;
  highlightClassName?: string;
};

export function VelocityHighlight({
  items,
  activeId,
  onSelect,
  className,
  highlightClassName,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Track mouse X for velocity deformation
  const mouseX = useMotionValue(0);
  const smoothX = useSpring(mouseX, { stiffness: 200, damping: 25 });
  const velocityX = useVelocity(smoothX);

  // Map velocity to scaleX/scaleY deformation
  const scaleX = useTransform(velocityX, [-1000, 0, 1000], [0.97, 1, 1.03]);
  const scaleY = useTransform(velocityX, [-1000, 0, 1000], [1.03, 1, 0.97]);

  const displayId = hoveredId ?? activeId;

  function handleMouseMove(e: React.MouseEvent) {
    mouseX.set(e.clientX);
  }

  return (
    <div
      ref={containerRef}
      className={cn("relative flex items-center gap-1 rounded-full bg-secondary/50 p-1", className)}
      onMouseMove={handleMouseMove}
    >
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelect(item.id)}
          onMouseEnter={() => setHoveredId(item.id)}
          onMouseLeave={() => setHoveredId(null)}
          className={cn(
            "relative z-10 flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors",
            displayId === item.id
              ? "text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {item.icon}
          {item.label}
        </button>
      ))}

      {/* Sliding highlight pill with velocity deformation */}
      <motion.div
        className={cn("absolute inset-y-1 z-0 rounded-full bg-primary", highlightClassName)}
        layoutId="velocity-highlight-pill"
        style={{
          scaleX: scaleX as MotionValue<number>,
          scaleY: scaleY as MotionValue<number>,
        }}
        transition={{ type: "spring", stiffness: 400, damping: 30 }}
      />
    </div>
  );
}
