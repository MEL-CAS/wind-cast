# WindCast

24h wind speed forecasting platform for industrial clients (construction, wind farm
operators). Dual-model pipeline (calm-regime XGBoost + strong-regime GRU/XGBoost-residual),
validated on two real sites:

- **Calm regime**: Milan — MAE 0.626 m/s, RMSE 0.890, MAPE 21.94%, R² 0.783 (n=19 021)
- **Strong regime**: Wellington, NZ — MAE 0.835 m/s, RMSE 1.255, MAPE 11.99%, R² 0.931 (n=7 689)

Two services, presented as one product: a Next.js frontend and a FastAPI backend wrapping the
trained model pipeline. See `C:\Users\melis\.claude\plans\robust-wobbling-lemur.md` for the full
build plan and rationale (why these sites and not the originally-planned ones).

## Repository layout

```
backend/
  main.py               FastAPI app (routes: /api/health, /api/geocode, /api/forecast)
  model/                data download, feature engineering, training scripts, trained
                         weights (backend/model/weights/*.json, *.pt, *.pkl)
  requirements.txt
frontend/
  app/[locale]/         Next.js App Router pages: /, /prediction, /methodologie, /contact
  components/           Nav, WindCanvas (hero), MapPicker, WindChart, ConfidenceGauge, ...
  i18n/, messages/       next-intl setup (fr default, en), messages/{fr,en}.json
  lib/                  api.ts (backend client), pdf.ts (client-side PDF export)
.env.example             template for both frontend/.env.local and backend env vars
```

## Run locally

Prerequisites: Python (repo's `venv/` already has torch/xgboost/sklearn/pandas/optuna
installed, matching `backend/requirements.txt`), Node.js 20+.

**Backend**
```bash
cd backend
../venv/Scripts/python -m pip install -r requirements.txt   # first time only
../venv/Scripts/python -m uvicorn main:app --port 8000
```
`GET /api/health` should return `{"status":"ok"}`.

**Frontend**
```bash
cd frontend
npm install                     # first time only
cp ../.env.example .env.local   # then edit NEXT_PUBLIC_API_URL if needed
npm run dev
```
Open http://localhost:3000.

## Retraining the models

The trained weights are already committed under `backend/model/weights/`. To retrain from
scratch (e.g. on new data or a new site), run from `backend/`:
```bash
../venv/Scripts/python -m model.train_calm     # XGBoost, calm regime (Milan)
../venv/Scripts/python -m model.train_strong   # GRU + XGBoost residual, strong regime (Wellington)
```
Both scripts download/cache Open-Meteo data under `backend/model/cache/`, print the 4
validation metrics (MAE/RMSE/MAPE/R²) to stdout, and overwrite the weight files. Update the
hardcoded metric numbers in `frontend/messages/{fr,en}.json` and
`frontend/app/[locale]/methodologie/page.tsx` if they change.

## Deployment

### Backend → Render (free tier)

1. Push this repo to a Git remote (private is fine).
2. On Render: New → Web Service → point at the repo, **root directory** `backend`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment variable: `FRONTEND_ORIGIN` = your Vercel URL (e.g. `https://windcast.vercel.app`).
6. Render's free tier sleeps after inactivity — first request after sleep takes ~30-50s
   (the frontend's cold-start loading state on `/prediction` is designed for this).

**Optional keep-alive**: to reduce how often the backend sleeps, use a free external cron
service (e.g. [cron-job.org](https://cron-job.org)) to `GET` your backend's `/api/health`
every 10-14 minutes. This does not require GitHub Actions or any CI — it's a plain HTTP ping
configured entirely on cron-job.org's side.

### Frontend → Vercel (free tier)

1. On Vercel: New Project → point at the repo, **root directory** `frontend`.
2. Framework preset: Next.js (auto-detected).
3. Environment variable: `NEXT_PUBLIC_API_URL` = your Render backend URL
   (e.g. `https://windcast-api.onrender.com`).
4. Deploy.

### Custom domain

Buy a domain (e.g. `windcast.io`), then in Vercel: Project → Settings → Domains → add it,
and follow Vercel's DNS instructions (usually an `A`/`CNAME` record at your registrar). No
backend-side domain config needed — the frontend calls the backend via
`NEXT_PUBLIC_API_URL`, which you can point at Render's default `*.onrender.com` URL or a
subdomain (e.g. `api.windcast.io`) if you also add a custom domain on the Render service.

## Where to change branding / contact info

- Contact email: `CONTACT_EMAIL` constant in `frontend/app/[locale]/contact/page.tsx`.
- Product name "WindCast": search `frontend/` for the string `WindCast` (nav logo, footer,
  page `<title>` in `app/[locale]/layout.tsx`, PDF export header in `lib/pdf.ts`).
- Site colors/tokens: `frontend/app/globals.css` (`@theme` block).

## Non-negotiables enforced in this codebase

- MAE, RMSE, MAPE, R² are always returned/shown together (`model/metrics.py`,
  `backend/main.py`, `frontend/app/[locale]/prediction/page.tsx`'s "Détails techniques").
  If one is genuinely unavailable, the API sets it to `null` with `mape_unavailable: true`
  rather than omitting it.
- Confidence score/label is never phrased as uniform precision across sites — see
  `backend/model/confidence.py` and the hedged language in `messages/{fr,en}.json`.
- The feature engineering and dual-model architecture in `backend/model/` were ported
  verbatim from the original research code (`src/`, `calm_wind_v2/` at the repo root) — no
  reimplementation drift from the validated pipeline.
