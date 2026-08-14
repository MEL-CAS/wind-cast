export type RegimeSegment = { label: string; regime: "calm" | "strong"; widthPct: number };

export default function RegimeBar({
  segments,
  calmLabel,
  strongLabel,
}: {
  segments: RegimeSegment[];
  calmLabel: string;
  strongLabel: string;
}) {
  return (
    <div>
      <div className="flex h-9.5 rounded-[9px] overflow-hidden my-1.5 border border-border">
        {segments.map((s, i) => (
          <span
            key={i}
            className={`flex items-center justify-center text-[10px] font-semibold ${
              s.regime === "calm"
                ? "bg-gradient-to-b from-[#3a4150] to-[#2b313c] text-text-secondary"
                : "bg-gradient-to-b from-accent-2 to-[#1fb98a] text-[#0c0e12]"
            }`}
            style={{ width: `${s.widthPct}%` }}
          >
            {s.label}
          </span>
        ))}
      </div>
      <div className="flex gap-4 text-[11px] text-text-secondary mt-3.5">
        <span className="flex items-center gap-1.5">
          <i className="inline-block w-2.5 h-2.5 rounded-[3px] bg-[#2b313c]" />
          {calmLabel}
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block w-2.5 h-2.5 rounded-[3px] bg-accent-2" />
          {strongLabel}
        </span>
      </div>
    </div>
  );
}
