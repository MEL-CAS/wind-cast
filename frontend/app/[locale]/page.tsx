"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import Reveal from "@/components/Reveal";
import ConfidenceGauge from "@/components/ConfidenceGauge";
import RegimeBar from "@/components/RegimeBar";
import WindChart from "@/components/WindChart";

const SPARK_HEIGHTS = [32, 54, 42, 70, 58, 88, 64, 48, 78, 60];

const DEMO_CHART = Array.from({ length: 12 }, (_, i) => ({
  time: new Date(Date.now() + i * 3600_000).toISOString(),
  wind_speed: Math.round((6 + Math.sin(i / 2) * 3 + i * 0.2) * 10) / 10,
}));

export default function HomePage() {
  const t = useTranslations();

  return (
    <>
      <section className="pt-24 pb-16 px-6 text-center max-w-[920px] mx-auto">
        <Reveal>
          <div className="inline-flex items-center gap-2.5 bg-card/60 border border-border-strong px-4 py-1.5 rounded-full text-xs text-text-secondary mb-7 backdrop-blur-md">
            <span className="relative w-1.75 h-1.75 rounded-full bg-accent-2">
              <span className="absolute inset-[-4px] rounded-full bg-accent-2 opacity-50 animate-[pulse-dot_2s_infinite]" />
            </span>
            {t("hero.badge")}
          </div>
        </Reveal>
        <Reveal delay={0.05}>
          <h1 className="text-[clamp(40px,7vw,68px)] font-black tracking-[-2px] leading-[1.05] mb-6">
            {t("hero.title1")}
            <br />
            <span className="bg-gradient-to-r from-accent via-accent-hi to-[#ffd0bd] bg-clip-text text-transparent">
              {t("hero.title2")}
            </span>
          </h1>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="text-lg text-text-secondary max-w-[600px] mx-auto mb-9">{t("hero.subtitle")}</p>
        </Reveal>
        <Reveal delay={0.15}>
          <div className="flex gap-3.5 justify-center flex-wrap">
            <Link
              href="/prediction"
              className="bg-gradient-to-br from-accent to-accent-hi text-[#1a0d05] px-6.5 py-3.5 rounded-[10px] font-bold text-[15px] shadow-[0_6px_24px_rgba(255,106,57,0.3)] hover:-translate-y-0.5 transition-transform"
            >
              {t("hero.ctaPrimary")} →
            </Link>
            <Link
              href="/methodologie"
              className="bg-card/60 border border-border-strong text-text-primary px-6.5 py-3.5 rounded-[10px] font-semibold text-[15px] backdrop-blur-md hover:border-accent transition-colors"
            >
              {t("hero.ctaSecondary")}
            </Link>
          </div>
        </Reveal>
        <Reveal delay={0.2}>
          <div className="flex gap-8 justify-center mt-11 flex-wrap">
            {[
              ["0.63", t("hero.trust.mae")],
              ["0.93", t("hero.trust.r2")],
              ["24 h", t("hero.trust.horizon")],
              ["10 m/s", t("hero.trust.threshold")],
            ].map(([n, l], i) => (
              <div key={i} className="flex flex-col items-center">
                <div className="text-[22px] font-extrabold tracking-tight">{n}</div>
                <div className="text-[10.5px] text-text-muted uppercase tracking-wider mt-0.5">{l}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="max-w-[1120px] mx-auto px-6 md:px-10 py-8 grid grid-cols-1 md:grid-cols-6 gap-4">
        <Reveal className="md:col-span-2 bg-card border border-border rounded-[18px] p-6 hover:border-border-strong hover:bg-card-hover hover:-translate-y-0.5 transition-all">
          <div className="text-[11px] text-text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-sm bg-accent" />
            {t("bento.metric.label")}
          </div>
          <div className="text-[44px] font-extrabold tracking-[-1.5px] leading-none">
            0.63<span className="text-[17px] text-text-secondary font-semibold"> m/s</span>
          </div>
          <div className="text-[12.5px] text-text-secondary mt-2">{t("bento.metric.sub")}</div>
          <div className="mt-4.5 flex items-end gap-[3px] h-10">
            {SPARK_HEIGHTS.map((h, i) => (
              <div
                key={i}
                className={`flex-1 rounded-t-sm ${i % 3 === 2 ? "bg-gradient-to-b from-accent-hi to-accent" : "bg-accent-soft"}`}
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.05} className="md:col-span-2 bg-card border border-border rounded-[18px] p-6 flex flex-col items-center text-center hover:border-border-strong hover:bg-card-hover transition-all">
          <div className="text-[11px] text-text-muted uppercase tracking-wide mb-3 self-start flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-sm bg-accent" />
            {t("bento.confidence.label")}
          </div>
          <ConfidenceGauge score={0.78} label={t("bento.confidence.unit")} />
          <div className="text-[12.5px] text-text-secondary mt-3.5">{t("hero.badge")}</div>
        </Reveal>

        <Reveal delay={0.1} className="md:col-span-2 bg-card border border-border rounded-[18px] p-6 hover:border-border-strong hover:bg-card-hover transition-all">
          <div className="text-[11px] text-text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-sm bg-accent" />
            {t("bento.regime.label")}
          </div>
          <RegimeBar
            segments={[
              { label: "00–08h", regime: "calm", widthPct: 33 },
              { label: "08–16h", regime: "strong", widthPct: 34 },
              { label: "16–24h", regime: "strong", widthPct: 33 },
            ]}
            calmLabel={t("bento.regime.calm")}
            strongLabel={t("bento.regime.strong")}
          />
        </Reveal>

        <Reveal delay={0.15} className="md:col-span-4 bg-card border border-border rounded-[18px] p-6 hover:border-border-strong hover:bg-card-hover transition-all">
          <div className="flex justify-between items-start">
            <div className="text-[11px] text-text-muted uppercase tracking-wide flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-sm bg-accent" />
              {t("bento.live.label")}
            </div>
            <div className="text-[10.5px] text-accent-2 flex items-center gap-1.5">
              <span className="w-1.75 h-1.75 rounded-full bg-accent-2 shadow-[0_0_8px_var(--color-accent-2)] animate-[blink-dot_1.6s_infinite]" />
              {t("bento.live.tag")}
            </div>
          </div>
          <div className="mt-3.5">
            <WindChart data={DEMO_CHART} />
          </div>
        </Reveal>

        <Reveal delay={0.2} className="md:col-span-2 rounded-[18px] overflow-hidden relative min-h-[190px] bg-[radial-gradient(circle_at_60%_45%,#1b2740,#0f1622)] hover:-translate-y-0.5 transition-transform">
          <div className="absolute inset-0" style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 26px), repeating-linear-gradient(90deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 26px)",
          }} />
          <div className="absolute inset-0 bg-gradient-to-t from-bg via-transparent to-transparent" />
          <div className="absolute top-[44%] left-[58%] w-4 h-4 rounded-full bg-accent shadow-[0_0_0_6px_var(--color-accent-soft),0_6px_14px_rgba(0,0,0,0.5)]">
            <span className="absolute inset-[-10px] rounded-full border border-accent opacity-60 animate-[ripple-pin_2.2s_infinite]" />
          </div>
          <div className="absolute bottom-3.5 left-4 right-4">
            <div className="text-sm font-bold">Wellington, NZ</div>
            <div className="text-[11px] text-text-secondary">{t("bento.map.caption")}</div>
          </div>
        </Reveal>

        {(["use1", "use2", "use3"] as const).map((key, i) => (
          <Reveal key={key} delay={0.05 * i} className="md:col-span-2 bg-card border border-border rounded-[18px] p-6 hover:border-border-strong hover:bg-card-hover hover:-translate-y-0.5 transition-all">
            <div className="w-10 h-10 rounded-[11px] bg-accent-soft border border-border flex items-center justify-center mb-3.5">
              <UseIcon variant={key} />
            </div>
            <h3 className="text-[16.5px] font-bold mb-1.5 tracking-tight">{t(`bento.${key}.title`)}</h3>
            <p className="text-[13px] text-text-secondary leading-relaxed">{t(`bento.${key}.text`)}</p>
          </Reveal>
        ))}
      </section>

      <section className="max-w-[1120px] mx-auto px-6 md:px-10 mt-3.5">
        <Reveal className="border border-border rounded-[18px] p-7 md:p-8 relative overflow-hidden bg-gradient-to-r from-card to-bg-soft flex items-center justify-between gap-7 flex-wrap">
          <div className="absolute -right-15 -top-15 w-65 h-65 rounded-full bg-[radial-gradient(circle,var(--color-accent-2-soft),transparent_70%)]" />
          <div className="relative z-10 max-w-[520px]">
            <h4 className="text-[17px] font-bold mb-1.5">{t("method.title")}</h4>
            <p className="text-[13.5px] text-text-secondary">{t("method.text")}</p>
          </div>
          <div className="relative z-10 flex gap-2.5 flex-wrap">
            {[
              ["0.63 / 0.84", t("method.mae")],
              ["0.89 / 1.26", t("method.rmse")],
              ["21.9% / 12.0%", t("method.mape")],
              ["0.78 / 0.93", t("method.r2")],
            ].map(([n, l], i) => (
              <div key={i} className="bg-card/60 border border-border-strong rounded-[10px] px-3.5 py-2.5 text-center backdrop-blur-sm">
                <div className="text-[15px] font-extrabold text-accent-2">{n}</div>
                <div className="text-[9.5px] text-text-muted tracking-wide mt-0.5">{l}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>
    </>
  );
}

function UseIcon({ variant }: { variant: "use1" | "use2" | "use3" }) {
  const common = { viewBox: "0 0 24 24", className: "w-5 h-5 stroke-accent fill-none", strokeWidth: 1.8 };
  if (variant === "use1")
    return (
      <svg {...common}>
        <path d="M4 21V9l7-4 7 4v12M4 21h14M8 21v-6h6v6M6 9l5-3 5 3" />
      </svg>
    );
  if (variant === "use2")
    return (
      <svg {...common}>
        <path d="M12 3l9 16H3L12 3z" />
        <path d="M12 10v4M12 17h.01" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />
    </svg>
  );
}
