const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type GeocodeResult = {
  name: string;
  country: string;
  admin: string;
  lat: number;
  lon: number;
};

export type ForecastPoint = { time: string; wind_speed: number; ci_low: number; ci_high: number };
export type RegimeHour = { time: string; regime: "calm" | "strong" };
export type Confidence = { score: number; label: string; reason: string };
export type Metrics = {
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  r2: number | null;
  mape_unavailable: boolean;
  validated_on: string;
};

export type ForecastResponse = {
  location: { name: string; lat: number; lon: number };
  forecast_24h: ForecastPoint[];
  regime_by_hour: RegimeHour[];
  model_used: "calm" | "strong" | "dual";
  confidence: Confidence;
  metrics: Metrics;
};

export class ColdStartError extends Error {}

export async function geocode(query: string, signal?: AbortSignal): Promise<GeocodeResult[]> {
  const res = await fetch(`${API_URL}/api/geocode?q=${encodeURIComponent(query)}`, { signal });
  if (!res.ok) throw new Error("Geocoding failed");
  const data = await res.json();
  return data.results;
}

export async function fetchForecast(
  lat: number,
  lon: number,
  name?: string,
  timeoutMs = 60000
): Promise<ForecastResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}/api/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, name }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || "Forecast request failed");
    }
    return await res.json();
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ColdStartError("Forecast request timed out (cold start?)");
    }
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

export async function pingHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
