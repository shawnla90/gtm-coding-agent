"use client";

import { animate } from "motion";
import { useEffect, useRef, useState } from "react";

type AnimateCountProps = {
  to: number;
  from?: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
};

/**
 * Counts up from `from` to `to` on mount using motion's `animate()`.
 * Accepts a `format` fn for localized output (e.g., formatNum).
 */
export function AnimateCount({
  to,
  from = 0,
  duration = 0.8,
  format = (n) => Math.round(n).toLocaleString(),
  className,
}: AnimateCountProps) {
  const [display, setDisplay] = useState<string>(format(from));
  const lastTargetRef = useRef<number>(from);

  useEffect(() => {
    const start = lastTargetRef.current;
    const controls = animate(start, to, {
      duration,
      ease: "easeOut",
      onUpdate: (latest) => setDisplay(format(latest)),
    });
    lastTargetRef.current = to;
    return () => controls.stop();
  }, [to, duration, format]);

  return <span className={className}>{display}</span>;
}
