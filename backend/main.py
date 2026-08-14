import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from model.geocode import geocode
from model.inference import forecast_24h

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI(title="WindCast API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ForecastRequest(BaseModel):
    lat: float
    lon: float
    name: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/geocode")
def api_geocode(q: str):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")
    return {"results": geocode(q)}


@app.post("/api/forecast")
def api_forecast(body: ForecastRequest):
    try:
        return forecast_24h(body.lat, body.lon, location_name=body.name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Forecast pipeline error: {e}")
