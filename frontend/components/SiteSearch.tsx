"use client";

import { useEffect, useRef, useState } from "react";
import { geocode, type GeocodeResult } from "@/lib/api";

export default function SiteSearch({
  placeholder,
  onSelect,
}: {
  placeholder: string;
  onSelect: (r: GeocodeResult) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timeout = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      try {
        const r = await geocode(query, controller.signal);
        setResults(r);
        setOpen(true);
      } catch {
        // ignore aborted/failed lookups
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => clearTimeout(timeout);
  }, [query]);

  return (
    <div className="relative">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className="w-full bg-card border border-border-strong rounded-[10px] px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent transition-colors min-h-11"
      />
      {loading && (
        <div className="absolute right-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full border-2 border-border-strong border-t-accent animate-spin" />
      )}
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1.5 w-full bg-card border border-border-strong rounded-[10px] overflow-hidden shadow-2xl max-h-64 overflow-y-auto">
          {results.map((r, i) => (
            <li key={i}>
              <button
                type="button"
                onMouseDown={() => {
                  onSelect(r);
                  setQuery(r.name);
                  setOpen(false);
                }}
                className="w-full text-left px-4 py-2.5 text-sm hover:bg-card-hover transition-colors min-h-11 flex flex-col justify-center"
              >
                <span className="text-text-primary">{r.name}</span>
                <span className="text-xs text-text-muted">
                  {[r.admin, r.country].filter(Boolean).join(", ")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
