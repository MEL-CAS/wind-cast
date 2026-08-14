"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// OpenFreeMap ships "liberty"/"bright"/"positron" — no key required. No dedicated
// dark style exists, so the container gets a CSS invert filter to match the theme.
const STYLE = "https://tiles.openfreemap.org/styles/liberty";

export default function MapPicker({
  lat,
  lon,
  onPick,
}: {
  lat: number;
  lon: number;
  onPick: (lat: number, lon: number) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: [lon, lat],
      zoom: 4,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const marker = new maplibregl.Marker({ color: "#ff6a39" }).setLngLat([lon, lat]).addTo(map);
    map.on("click", (e) => {
      marker.setLngLat(e.lngLat);
      onPick(e.lngLat.lat, e.lngLat.lng);
    });
    mapRef.current = map;
    markerRef.current = marker;
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (markerRef.current && mapRef.current) {
      markerRef.current.setLngLat([lon, lat]);
      mapRef.current.flyTo({ center: [lon, lat], zoom: Math.max(mapRef.current.getZoom(), 6) });
    }
  }, [lat, lon]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[280px] rounded-[14px] overflow-hidden [&_.maplibregl-canvas]:brightness-75 [&_.maplibregl-canvas]:invert-[0.92] [&_.maplibregl-canvas]:hue-rotate-180"
    />
  );
}
