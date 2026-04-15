"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

/**
 * HoverExpand — spring-scale on hover, subtle lift + border accent.
 *
 * Thin wrapper around card children. Pulls a grid card forward on hover to
 * reduce click depth — feels "alive" without adding layout shift.
 *
 * Usage:
 *   <HoverExpand>
 *     <Card>...</Card>
 *   </HoverExpand>
 */

type Props = {
  children: ReactNode;
  className?: string;
};

export function HoverExpand({ children, className }: Props) {
  return (
    <motion.div
      className={className}
      whileHover={{ y: -2, scale: 1.01 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
    >
      {children}
    </motion.div>
  );
}
