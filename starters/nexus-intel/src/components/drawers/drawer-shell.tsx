"use client";

import { Sheet, SheetContent } from "@/components/ui/sheet";
import { SignalDrawer } from "./signal-drawer";
import { EngagerDrawer } from "./engager-drawer";
import { SourceDrawer } from "./source-drawer";
import type { DrawerTarget, DrawerData } from "./types";

interface Props {
  target: DrawerTarget | null;
  data: DrawerData | null;
  onClose: () => void;
  onSwap: (target: DrawerTarget) => void;
}

export function DrawerShell({ target, data, onClose, onSwap }: Props) {
  const open = target !== null;
  const bodyKey = target ? `${target.type}-${target.id}` : "empty";

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-[380px] sm:max-w-[420px] overflow-y-auto"
      >
        <div key={bodyKey} className="animate-in fade-in-0 duration-150">
          {data === null && target !== null && <DrawerSkeleton />}
          {data?.type === "signal" && (
            <SignalDrawer data={data.data} onSwap={onSwap} />
          )}
          {data?.type === "source" && (
            <SourceDrawer data={data.data} onSwap={onSwap} />
          )}
          {data?.type === "engager" && <EngagerDrawer data={data.data} />}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function DrawerSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 animate-pulse rounded-full bg-secondary/40" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-3/4 animate-pulse rounded bg-secondary/40" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-secondary/30" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 animate-pulse rounded bg-secondary/30" />
        <div className="h-3 w-5/6 animate-pulse rounded bg-secondary/30" />
        <div className="h-3 w-4/6 animate-pulse rounded bg-secondary/30" />
      </div>
      <div className="h-16 animate-pulse rounded-lg bg-secondary/20" />
    </div>
  );
}
