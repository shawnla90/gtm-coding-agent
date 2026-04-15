"use client";

import { useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";

type Props = {
  /** Gap between pixels in px (default 12) */
  gap?: number;
  /** Animation speed 0–100 (default 40) */
  speed?: number;
  /** Reveal pattern (default "cursor") */
  pattern?: "center" | "cursor" | "spiral" | "edges" | "random";
  /** Pixel colors (default: Apollo teal shades) */
  colors?: string[];
  className?: string;
  children?: React.ReactNode;
};

const defaultColors = ["#D4A843", "#B8922E", "#8B6914", "#EC4899"];

class Pixel {
  x: number;
  y: number;
  color: string;
  size: number;
  targetSize: number;
  speed: number;
  alpha: number;
  targetAlpha: number;

  constructor(x: number, y: number, color: string, speed: number) {
    this.x = x;
    this.y = y;
    this.color = color;
    this.size = 0;
    this.targetSize = 0;
    this.speed = 0.02 + Math.random() * speed * 0.001;
    this.alpha = 0;
    this.targetAlpha = 0;
  }

  appear() {
    this.targetSize = 2 + Math.random() * 3;
    this.targetAlpha = 0.3 + Math.random() * 0.7;
  }

  disappear() {
    this.targetSize = 0;
    this.targetAlpha = 0;
  }

  update() {
    this.size += (this.targetSize - this.size) * this.speed;
    this.alpha += (this.targetAlpha - this.alpha) * this.speed;
  }

  draw(ctx: CanvasRenderingContext2D) {
    if (this.size < 0.1) return;
    ctx.globalAlpha = this.alpha;
    ctx.fillStyle = this.color;
    ctx.fillRect(
      this.x - this.size / 2,
      this.y - this.size / 2,
      this.size,
      this.size
    );
  }
}

export function PixelBackground({
  gap = 12,
  speed = 40,
  pattern = "cursor",
  colors = defaultColors,
  className,
  children,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pixelsRef = useRef<Pixel[]>([]);
  const animRef = useRef<number>(0);
  const mouseRef = useRef({ x: -1, y: -1, active: false });

  const initPixels = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    const pixels: Pixel[] = [];
    for (let x = gap; x < rect.width; x += gap) {
      for (let y = gap; y < rect.height; y += gap) {
        const color = colors[Math.floor(Math.random() * colors.length)];
        pixels.push(new Pixel(x, y, color, speed));
      }
    }
    pixelsRef.current = pixels;
  }, [gap, speed, colors]);

  useEffect(() => {
    initPixels();

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function animate() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const mouse = mouseRef.current;
      const radius = 150;

      for (const pixel of pixelsRef.current) {
        if (mouse.active && pattern === "cursor") {
          const dx = pixel.x - mouse.x;
          const dy = pixel.y - mouse.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < radius) {
            pixel.appear();
          } else {
            pixel.disappear();
          }
        }
        pixel.update();
        pixel.draw(ctx);
      }

      animRef.current = requestAnimationFrame(animate);
    }

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [initPixels, pattern]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ro = new ResizeObserver(() => initPixels());
    ro.observe(canvas);
    return () => ro.disconnect();
  }, [initPixels]);

  function onMouseMove(e: React.MouseEvent) {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    mouseRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      active: true,
    };
  }

  function onMouseLeave() {
    mouseRef.current.active = false;
    for (const pixel of pixelsRef.current) {
      pixel.disappear();
    }
  }

  return (
    <div
      className={cn("relative", className)}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full"
        aria-hidden
      />
      {children && <div className="relative z-[1]">{children}</div>}
    </div>
  );
}
