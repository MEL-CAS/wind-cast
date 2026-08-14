"use client";

import { useTranslations } from "next-intl";
import Reveal from "@/components/Reveal";

const CALM = { mae: "0.626", rmse: "0.890", mape: "21.94%", r2: "0.783", n: "19 021" };
const STRONG = { mae: "0.835", rmse: "1.255", mape: "11.99%", r2: "0.931", n: "7 689" };

function MetricRow({ site, m }: { site: string; m: typeof CALM }) {
  return (
    <div className="bg-bg-soft border border-border rounded-[14px] p-5">
      <p className="font-semibold text-sm mb-3">{site}</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-lg font-extrabold text-accent-2">{m.mae}</div>
          <div className="text-[10px] text-text-muted uppercase">MAE m/s</div>
        </div>
        <div>
          <div className="text-lg font-extrabold text-accent-2">{m.rmse}</div>
          <div className="text-[10px] text-text-muted uppercase">RMSE m/s</div>
        </div>
        <div>
          <div className="text-lg font-extrabold text-accent-2">{m.mape}</div>
          <div className="text-[10px] text-text-muted uppercase">MAPE</div>
        </div>
        <div>
          <div className="text-lg font-extrabold text-accent-2">{m.r2}</div>
          <div className="text-[10px] text-text-muted uppercase">R²</div>
        </div>
      </div>
      <p className="text-[11px] text-text-muted mt-3">n = {m.n}</p>
    </div>
  );
}

export default function MethodologyPage() {
  const t = useTranslations("methodology");

  return (
    <div className="max-w-[900px] mx-auto px-6 md:px-10 py-12">
      <Reveal>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-2">{t("title")}</h1>
        <p className="text-text-secondary mb-10">{t("subtitle")}</p>
      </Reveal>

      <Reveal delay={0.05} className="bg-card border border-border rounded-[18px] p-7 mb-5">
        <h2 className="font-bold text-lg mb-3">{t("pipeline.title")}</h2>
        <p className="text-sm text-text-secondary leading-relaxed">{t("pipeline.text")}</p>
      </Reveal>

      <Reveal delay={0.1} className="bg-card border border-border rounded-[18px] p-7 mb-5">
        <h2 className="font-bold text-lg mb-4">{t("validation.title")}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MetricRow site={t("validation.calmSite")} m={CALM} />
          <MetricRow site={t("validation.strongSite")} m={STRONG} />
        </div>
        <p className="text-[11px] text-text-muted mt-4">{t("mapeNote")}</p>
      </Reveal>

      <Reveal delay={0.15} className="bg-card border border-border rounded-[18px] p-7">
        <h2 className="font-bold text-lg mb-3">{t("limits.title")}</h2>
        <p className="text-sm text-text-secondary leading-relaxed">{t("limits.text")}</p>
      </Reveal>
    </div>
  );
}
