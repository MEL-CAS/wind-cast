"""Ported from src/opendata.geocode_location."""
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(query, count=5, language="fr"):
    params = {"name": query, "count": count, "language": language}
    r = requests.get(GEOCODE_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    return [
        {
            "name": it["name"],
            "country": it.get("country", ""),
            "admin": it.get("admin1", ""),
            "lat": it["latitude"],
            "lon": it["longitude"],
        }
        for it in results
    ]
