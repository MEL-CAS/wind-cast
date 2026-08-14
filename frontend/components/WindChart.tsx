"use client";

import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TooltipContentProps } from "recharts";

export type ChartPoint = { time: string; wind_speed: number; ci_low?: number; ci_high?: number };

// Recharts' default Tooltip shows one row per <Area>/<Line> on the chart —
// including the invisible ci_high band, which produced two "wind" rows with
// different values. This filters down to the actual wind_speed series only.
function WindTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const point = payload.find((p) => p.dataKey === "wind_speed");
  if (!point) return null;
  return (
    <div
      style={{
        background: "var(--color-card)",
        border: "1px solid var(--color-border-strong)",
        borderRadius: 10,
        fontSize: 12,
        padding: "8px 12px",
      }}
    >
      <div style={{ color: "var(--color-text-secondary)", marginBottom: 2 }}>{label}</div>
      <div style={{ color: "var(--color-accent)", fontWeight: 600 }}>{point.value} m/s</div>
    </div>
  );
}

export default function WindChart({ data }: { data: ChartPoint[] }) {
  const formatted = data.map((d) => ({
    ...d,
    hh: new Date(d.time).toLocaleTimeString([], { hour: "2-digit" }),
    band: d.ci_high != null && d.ci_low != null ? d.ci_high - d.ci_low : 0,
  }));

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formatted} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="windFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="hh" stroke="var(--color-text-muted)" fontSize={10} tickLine={false} axisLine={false} />
          <YAxis stroke="var(--color-text-muted)" fontSize={10} tickLine={false} axisLine={false} width={30} />
          <Tooltip content={WindTooltip} />
          {formatted[0]?.ci_high != null && (
            <Area
              type="monotone"
              dataKey="ci_high"
              stroke="none"
              fill="var(--color-accent-soft)"
              fillOpacity={0.5}
              isAnimationActive={false}
            />
          )}
          <Area
            type="monotone"
            dataKey="wind_speed"
            stroke="var(--color-accent)"
            strokeWidth={2.5}
            fill="url(#windFill)"
            animationDuration={1200}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
