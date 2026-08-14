"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import Reveal from "@/components/Reveal";
import SiteSearch from "@/components/SiteSearch";
import ColdStartLoader from "@/components/ColdStartLoader";
import ConfidenceGauge from "@/components/ConfidenceGauge";
import WindChart from "@/components/WindChart";
import RegimeBar, { type RegimeSegment } from "@/components/RegimeBar";
import { fetchForecast, type ForecastResponse, type GeocodeResult } from "@/lib/api";
import { exportForecastPdf } from "@/lib/pdf";

const MapPicker = dynamic(() => import("@/components/MapPicker"), { ssr: false });

const DEFAULT_SITE = { lat: -41.2865, lon: 174.7762, name: "Wellington, NZ" };
const REFRESH_MS = 20 * 60 * 1000;

type Site = { lat: number; lon: number; name: string };
type CompareSite = Site & { id: string; forecast: ForecastResponse | null; loading: boolean; error: boolean };

function regimeSegments(forecast: ForecastResponse, calmLabel: string, strongLabel: string): RegimeSegment[] {
  const hours = forecast.regime_by_hour;
  const segments: RegimeSegment[] = [];
  let i = 0;
  while (i < hours.length) {
    const regime = hours[i].regime;
    let j = i;
    while (j < hours.length && hours[j].regime === regime) j++;
    const startH = new Date(hours[i].time).getHours();
    const endH = new Date(hours[j - 1].time).getHours();
    segments.push({
      regime,
      widthPct: ((j - i) / hours.length) * 100,
      label: `${String(startH).padStart(2, "0")}–${String((endH + 1) % 24).padStart(2, "0")}h`,
    });
    i = j;
  }
  return segments.map((s) => ({ ...s, label: s.regime === "calm" ? `${s.label} ${calmLabel[0]}` : `${s.label} ${strongLabel[0]}` }));
}

export default function PredictionPage() {
  const t = useTranslations("prediction");
  const tb = useTranslations("bento");
  const [site, setSite] = useState<Site>(DEFAULT_SITE);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [compareSites, setCompareSites] = useState<CompareSite[]>([]);
  const reportRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async (s: Site) => {
    setLoading(true);
    setError(false);
    try {
      const r = await fetchForecast(s.lat, s.lon, s.name);
      setForecast(r);
      setLastUpdated(new Date());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(site);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site]);

  useEffect(() => {
    const interval = setInterval(() => load(site), REFRESH_MS);
    return () => clearInterval(interval);
  }, [site, load]);

  const handleGeocodePick = (r: GeocodeResult) => setSite({ lat: r.lat, lon: r.lon, name: r.name });
  const handleMapPick = (lat: number, lon: number) => setSite({ lat, lon, name: `${lat.toFixed(3)}, ${lon.toFixed(3)}` });

  const addCompareSite = (r: GeocodeResult) => {
    const id = `${r.lat}-${r.lon}-${Date.now()}`;
    setCompareSites((prev) => [...prev, { lat: r.lat, lon: r.lon, name: r.name, id, forecast: null, loading: true, error: false }]);
    fetchForecast(r.lat, r.lon, r.name)
      .then((f) => setCompareSites((prev) => prev.map((c) => (c.id === id ? { ...c, forecast: f, loading: false } : c))))
      .catch(() => setCompareSites((prev) => prev.map((c) => (c.id === id ? { ...c, error: true, loading: false } : c))));
  };

  const removeCompareSite = (id: string) => setCompareSites((prev) => prev.filter((c) => c.id !== id));

  const handleExportPdf = async () => {
    if (!reportRef.current || !forecast) return;
    await exportForecastPdf(reportRef.current, forecast);
  };

  return (
    <div className="max-w-[1120px] mx-auto px-6 md:px-10 py-12">
      <Reveal>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-2">{t("title")}</h1>
        <p className="text-text-secondary mb-8 max-w-xl">{t("subtitle")}</p>
      </Reveal>

      <Reveal delay={0.05} className="grid grid-cols-1 lg:grid-cols-[1fr_1.1fr] gap-4 mb-4">
        <div className="min-w-0 bg-card border border-border rounded-[18px] p-6">
          <SiteSearch placeholder={t("searchPlaceholder")} onSelect={handleGeocodePick} />
          <p className="text-xs text-text-muted mt-3">{t("mapHint")}</p>
          <div className="mt-3 h-[300px] rounded-[14px] overflow-hidden border border-border">
            <MapPicker lat={site.lat} lon={site.lon} onPick={handleMapPick} />
          </div>
        </div>

        <div className="min-w-0 bg-card border border-border rounded-[18px] p-6 flex flex-col">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-bold text-lg">{site.name}</h2>
            {lastUpdated && !loading && (
              <span className="text-xs text-text-muted">
                {t("lastUpdated")} {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>

          {loading && !forecast && <ColdStartLoader title={t("coldStart.title")} text={t("coldStart.text")} />}
          {error && !loading && <p className="text-sm text-accent mt-6">{t("error")}</p>}

          {forecast && (
            <div ref={reportRef} className="mt-3">
              <p className="text-xs uppercase tracking-wide text-text-muted mb-1">{t("chartTitle")}</p>
              <WindChart data={forecast.forecast_24h} />

              <p className="text-xs uppercase tracking-wide text-text-muted mt-5 mb-1">{t("regimeTimeline")}</p>
              <RegimeBar
                segments={regimeSegments(forecast, tb("regime.calm"), tb("regime.strong"))}
                calmLabel={tb("regime.calm")}
                strongLabel={tb("regime.strong")}
              />

              <div className="flex items-center gap-6 mt-5">
                <ConfidenceGauge score={forecast.confidence.score} label={tb("confidence.unit")} />
                <div>
                  <p className="text-sm font-semibold capitalize">{forecast.confidence.label}</p>
                  <p className="text-xs text-text-secondary mt-1 max-w-xs">{forecast.confidence.reason}</p>
                  <p className="text-[11px] text-text-muted mt-1.5">{t("confidenceNote")}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </Reveal>

      {forecast && (
        <Reveal delay={0.1} className="bg-card border border-border rounded-[18px] p-6 mb-4">
          <button
            onClick={() => setDetailsOpen((o) => !o)}
            className="flex items-center justify-between w-full text-left min-h-11"
          >
            <span className="font-semibold text-sm">{t("details")}</span>
            <span className={`transition-transform ${detailsOpen ? "rotate-180" : ""}`}>⌄</span>
          </button>
          {detailsOpen && (
            <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
              <MetricChip label="MAE" value={`${forecast.metrics.mae ?? "—"} m/s`} />
              <MetricChip label="RMSE" value={`${forecast.metrics.rmse ?? "—"} m/s`} />
              <MetricChip
                label="MAPE"
                value={forecast.metrics.mape_unavailable ? "n/d" : `${forecast.metrics.mape}%`}
              />
              <MetricChip label="R²" value={`${forecast.metrics.r2 ?? "—"}`} />
              <MetricChip label={t("modelUsed")} value={forecast.model_used} />
            </div>
          )}
        </Reveal>
      )}

      {forecast && (
        <Reveal delay={0.12} className="flex justify-end mb-10">
          <button
            onClick={handleExportPdf}
            className="bg-gradient-to-br from-accent to-accent-hi text-[#1a0d05] font-bold text-sm px-5 py-3 rounded-[10px] min-h-11 hover:-translate-y-0.5 transition-transform"
          >
            {t("exportPdf")}
          </button>
        </Reveal>
      )}

      <Reveal delay={0.15}>
        <h2 className="font-bold text-xl mb-3">{t("compareTitle")}</h2>
        <div className="mb-4 max-w-md">
          <SiteSearch placeholder={t("addCompare")} onSelect={addCompareSite} />
        </div>
        {compareSites.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {compareSites.map((c) => (
              <div key={c.id} className="min-w-0 bg-card border border-border rounded-[16px] p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-sm">{c.name}</h3>
                  <button
                    onClick={() => removeCompareSite(c.id)}
                    className="text-xs text-text-muted hover:text-accent min-h-11 px-2"
                  >
                    {t("removeSite")}
                  </button>
                </div>
                {c.loading && <ColdStartLoader title={t("coldStart.title")} text={t("coldStart.text")} />}
                {c.error && <p className="text-sm text-accent">{t("error")}</p>}
                {c.forecast && (
                  <>
                    <WindChart data={c.forecast.forecast_24h} />
                    <div className="flex items-center gap-3 mt-3">
                      <ConfidenceGauge score={c.forecast.confidence.score} label={tb("confidence.unit")} />
                      <p className="text-xs text-text-secondary">{c.forecast.confidence.reason}</p>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </Reveal>
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-bg-soft border border-border rounded-[10px] px-3 py-2.5 text-center">
      <div className="text-sm font-extrabold text-accent-2">{value}</div>
      <div className="text-[9.5px] text-text-muted uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
}
