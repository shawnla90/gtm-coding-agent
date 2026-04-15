"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  motion,
  useMotionValue,
  useSpring,
  useVelocity,
  useTransform,
} from "motion/react";
import { useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Zap, Radio, Globe, Users } from "lucide-react";

const NAV_ITEMS = [
  { id: "/", label: "Command Center", icon: Zap },
  { id: "/signals", label: "Signals", icon: Radio },
  { id: "/nexus", label: "Nexus", icon: Globe },
  { id: "/leads", label: "Leads", icon: Users },
] as const;

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [pillStyle, setPillStyle] = useState({ left: 0, width: 0 });
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Velocity tracking for deformation
  const mouseX = useMotionValue(0);
  const smoothX = useSpring(mouseX, { stiffness: 200, damping: 25 });
  const velocityX = useVelocity(smoothX);
  const scaleX = useTransform(velocityX, [-1500, 0, 1500], [0.96, 1, 1.04]);
  const scaleY = useTransform(velocityX, [-1500, 0, 1500], [1.04, 1, 0.96]);

  const activeId = hoveredId ?? pathname;

  // Measure the active button and position the pill
  useEffect(() => {
    const el = itemRefs.current.get(activeId);
    const container = containerRef.current;
    if (!el || !container) return;

    const elRect = el.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    setPillStyle({
      left: elRect.left - containerRect.left,
      width: elRect.width,
    });
  }, [activeId]);

  function handleMouseMove(e: React.MouseEvent) {
    mouseX.set(e.clientX);
  }

  return (
    <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border/50 bg-background/80 px-6 backdrop-blur-md">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary">
          <Zap className="h-3.5 w-3.5 text-primary-foreground" />
        </div>
        <span className="text-sm font-semibold tracking-tight">
          Apollo Intel
        </span>
      </div>

      {/* Nav tabs with velocity highlight */}
      <nav
        ref={containerRef}
        className="relative flex items-center gap-0.5 rounded-full bg-secondary/60 p-1"
        onMouseMove={handleMouseMove}
      >
        {/* Sliding pill */}
        <motion.div
          className="absolute inset-y-1 z-0 rounded-full bg-primary/90"
          animate={{
            left: pillStyle.left,
            width: pillStyle.width,
          }}
          style={{ scaleX, scaleY }}
          transition={{ type: "spring", stiffness: 400, damping: 32 }}
        />

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeId === item.id;
          return (
            <button
              key={item.id}
              ref={(el) => {
                if (el) itemRefs.current.set(item.id, el);
              }}
              onClick={() => router.push(item.id)}
              onMouseEnter={() => setHoveredId(item.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={cn(
                "relative z-10 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors duration-150",
                isActive
                  ? "text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Right: demo badge */}
      <div className="flex items-center gap-2">
        <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[10px] font-medium text-primary">
          Demo
        </span>
      </div>
    </header>
  );
}
