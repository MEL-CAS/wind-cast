"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// CARTO's free "dark_all" raster basemap — a real dark style (labels/roads
// included, no CSS-filter hack needed), no API key required. Always requests
// @2x tiles for sharp rendering (CARTO's URL scheme, not the "{r}" Leaflet
// retina token — that token isn't recognized by MapLibre, so it was leaking
// into the URL literally as "%7Br%7D" and 404ing every single tile request).
// Previously used OpenFreeMap's "liberty" style inverted via CSS filter,
// which was both too dark/murky and too low-res — this replaces that entirely.
const DARK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "carto-dark": {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO",
    },
  },
  layers: [{ id: "carto-dark-layer", type: "raster", source: "carto-dark", minzoom: 0, maxzoom: 20 }],
};

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
      style: DARK_STYLE,
      center: [lon, lat],
      zoom: 6,
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
      mapRef.current.flyTo({ center: [lon, lat], zoom: Math.max(mapRef.current.getZoom(), 9) });
    }
  }, [lat, lon]);

  return <div ref={containerRef} className="w-full h-full min-h-[280px] rounded-[14px] overflow-hidden" />;
}
