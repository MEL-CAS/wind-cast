"use client";

import { useEffect, useRef, useState } from "react";

export default function ConfidenceGauge({ score, label }: { score: number; label: string }) {
  const [angle, setAngle] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setAngle(score), 300);
    return () => clearTimeout(t);
  }, [score]);

  const pct = Math.round(score * 100);

  return (
    <div
      ref={ref}
      className="relative w-[118px] h-[118px] rounded-full mx-auto"
      style={{
        background: `conic-gradient(var(--color-accent-2) ${angle}turn, var(--color-border) ${angle}turn)`,
        transition: "background 1.2s ease",
      }}
    >
      <div className="absolute inset-3 rounded-full bg-card flex flex-col items-center justify-center">
        <span className="text-[23px] font-extrabold">
          {pct}
          <span className="text-[13px]">%</span>
        </span>
        <span className="text-[8.5px] text-text-muted tracking-widest font-mono">{label}</span>
      </div>
    </div>
  );
}
