"use client";

import { useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CopyButton({
  text,
  label = "Copy opener",
}: {
  text: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // noop — clipboard API not available
    }
  };

  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      onClick={onCopy}
      className="h-7 gap-1.5 text-[11px]"
    >
      {copied ? (
        <>
          <CheckIcon className="size-3 text-emerald-500" />
          Copied
        </>
      ) : (
        <>
          <CopyIcon className="size-3" />
          {label}
        </>
      )}
    </Button>
  );
}
