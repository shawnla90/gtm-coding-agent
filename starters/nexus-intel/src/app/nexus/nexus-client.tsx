"use client";

import { useState, useCallback, useRef, useTransition } from "react";
import { ForceNexus, type NexusNode } from "@/components/force-nexus";
import {
  fetchSignalDrawerData,
  fetchEngagerDrawerData,
  fetchSourceDrawerData,
} from "./actions";
import { DrawerShell } from "@/components/drawers/drawer-shell";
import type {
  DrawerTarget,
  DrawerData,
  SignalDrawerData,
  EngagerDrawerData,
  SourceDrawerData,
} from "@/components/drawers/types";

interface Props {
  nodes: NexusNode[];
  edges: { id: string; source: string; target: string; weight: number }[];
}

export function NexusClient({ nodes, edges }: Props) {
  const [target, setTarget] = useState<DrawerTarget | null>(null);
  const [data, setData] = useState<DrawerData | null>(null);
  const requestIdRef = useRef(0);
  const [, startTransition] = useTransition();

  const openDrawer = useCallback(async (next: DrawerTarget) => {
    const reqId = ++requestIdRef.current;
    setTarget(next);
    setData(null);

    if (next.type === "signal") {
      const payload: SignalDrawerData | null = await fetchSignalDrawerData(next.id);
      if (requestIdRef.current !== reqId) return;
      if (!payload) {
        setTarget(null);
        return;
      }
      startTransition(() => {
        setData({ type: "signal", data: payload });
      });
      return;
    }

    if (next.type === "engager") {
      const payload: EngagerDrawerData | null = await fetchEngagerDrawerData(next.id);
      if (requestIdRef.current !== reqId) return;
      if (!payload) {
        setTarget(null);
        return;
      }
      startTransition(() => {
        setData({ type: "engager", data: payload });
      });
      return;
    }

    if (next.type === "source") {
      const payload: SourceDrawerData | null = await fetchSourceDrawerData(next.id);
      if (requestIdRef.current !== reqId) return;
      if (!payload) {
        setTarget(null);
        return;
      }
      startTransition(() => {
        setData({ type: "source", data: payload });
      });
      return;
    }
  }, []);

  const closeDrawer = useCallback(() => {
    setTarget(null);
    setData(null);
  }, []);

  return (
    <>
      <ForceNexus
        nodes={nodes}
        edges={edges}
        className="h-full"
        onNodeClick={openDrawer}
      />
      <DrawerShell
        target={target}
        data={data}
        onClose={closeDrawer}
        onSwap={openDrawer}
      />
    </>
  );
}
