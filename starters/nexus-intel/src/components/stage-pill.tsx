"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ChevronDownIcon } from "lucide-react";

const STAGES = [
  "stranger",
  "aware",
  "interested",
  "engaged",
  "conversing",
  "warm",
  "client",
] as const;

const STAGE_COLORS: Record<string, string> = {
  stranger: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  aware: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  interested: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  engaged: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  conversing: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  warm: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  client: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

export function StagePill({
  personId,
  currentStage,
}: {
  personId: number;
  currentStage: string;
}) {
  const [open, setOpen] = useState(false);
  const [stage, setStage] = useState(currentStage);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleChange = (newStage: string) => {
    setOpen(false);
    if (newStage === stage) return;
    const previous = stage;
    setStage(newStage);
    startTransition(async () => {
      const res = await fetch("/api/relationships/stage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ personId, stage: newStage }),
      });
      if (!res.ok) {
        setStage(previous);
        return;
      }
      router.refresh();
    });
  };

  const color = STAGE_COLORS[stage] ?? STAGE_COLORS.stranger;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={isPending}
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium capitalize transition-opacity ${color} ${isPending ? "opacity-60" : "hover:opacity-90"}`}
      >
        {stage}
        <ChevronDownIcon className="size-3" />
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="absolute right-0 top-full mt-1 z-20 min-w-[140px] rounded-lg border border-border bg-popover shadow-lg p-1">
            {STAGES.map((s) => (
              <button
                key={s}
                onClick={() => handleChange(s)}
                className={`w-full text-left px-2.5 py-1.5 rounded text-xs capitalize hover:bg-muted ${s === stage ? "font-semibold" : ""}`}
              >
                {s}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
