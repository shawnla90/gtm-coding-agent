"use client";

import { motion, LayoutGroup } from "motion/react";
import Link from "next/link";

type Tab = {
  label: string;
  href: string;
  icon?: React.ReactNode;
};

type MotionTabsMenuProps = {
  tabs: Tab[];
  activeHref: string;
  className?: string;
};

/**
 * Pill-style tab bar with a spring-animated active indicator.
 * Uses LayoutGroup + layoutId so the indicator slides smoothly between tabs.
 */
export function MotionTabsMenu({ tabs, activeHref, className = "" }: MotionTabsMenuProps) {
  return (
    <LayoutGroup id="motion-tabs">
      <div
        className={`inline-flex items-center gap-1 rounded-full border border-border bg-card/60 backdrop-blur p-1 ${className}`}
      >
        {tabs.map((tab) => {
          const isActive = tab.href === activeHref;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`relative inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
                isActive
                  ? "text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {isActive && (
                <motion.span
                  layoutId="motion-tab-bg"
                  className="absolute inset-0 rounded-full bg-primary"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative z-10 inline-flex items-center gap-1.5">
                {tab.icon}
                {tab.label}
              </span>
            </Link>
          );
        })}
      </div>
    </LayoutGroup>
  );
}
