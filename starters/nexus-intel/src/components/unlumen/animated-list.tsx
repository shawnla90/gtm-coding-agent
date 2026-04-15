"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

/**
 * AnimatedList — spring-stagger fade-in for card grids.
 *
 * Wrap a grid's children to have them pop into place as the user lands on a
 * page. Used on /signals, /insights, and anywhere a fresh feed lands — makes
 * the dashboard feel alive vs. diagrammatic.
 *
 * Usage:
 *   <AnimatedList className="grid grid-cols-3 gap-3">
 *     {items.map(i => <Card key={i.id}>...</Card>)}
 *   </AnimatedList>
 */

type Props = {
  children: ReactNode;
  className?: string;
  /** Delay between each child (default 40ms) */
  stagger?: number;
};

const container = (stagger: number) => ({
  hidden: {},
  show: {
    transition: {
      staggerChildren: stagger / 1000,
      delayChildren: 0.02,
    },
  },
});

const item = {
  hidden: { opacity: 0, y: 8, scale: 0.98 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 260, damping: 22 },
  },
};

export function AnimatedList({ children, className, stagger = 40 }: Props) {
  const childArray = Array.isArray(children) ? children : [children];
  return (
    <motion.div
      className={className}
      variants={container(stagger)}
      initial="hidden"
      animate="show"
    >
      {childArray.map((child, i) => (
        <motion.div key={(child as { key?: string })?.key ?? i} variants={item}>
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
