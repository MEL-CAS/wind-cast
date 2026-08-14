"use client";

import { useEffect, useRef } from "react";

type Particle = { x: number; y: number; life: number };

export default function WindCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;

    let W = 0;
    let H = 0;
    let raf = 0;
    const N = window.innerWidth < 820 ? 60 : 130;
    let particles: Particle[] = [];

    function resize() {
      W = canvas!.width = canvas!.offsetWidth;
      H = canvas!.height = canvas!.offsetHeight;
    }

    function field(px: number, py: number, t: number) {
      return (
        Math.sin(px * 0.0016 + t * 0.0002) * 1.4 +
        Math.cos(py * 0.0018 - t * 0.00015) * 1.1 +
        Math.sin((px + py) * 0.0009) * 0.7
      );
    }

    function mk(): Particle {
      return { x: Math.random() * W, y: Math.random() * H, life: Math.random() * 120 + 40 };
    }

    resize();
    particles = Array.from({ length: N }, mk);
    window.addEventListener("resize", resize);

    function loop(t: number) {
      ctx!.clearRect(0, 0, W, H);
      for (const p of particles) {
        const a = field(p.x, p.y, t);
        p.x += Math.cos(a) * 0.9;
        p.y += Math.sin(a) * 0.9;
        p.life -= 1;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, 1.1, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(255,138,99,0.5)";
        ctx!.fill();
        if (p.life < 0 || p.x < 0 || p.x > W || p.y < 0 || p.y > H) {
          Object.assign(p, mk());
        }
      }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className="fixed inset-0 z-0 h-full w-full pointer-events-none opacity-55"
      aria-hidden="true"
    />
  );
}
