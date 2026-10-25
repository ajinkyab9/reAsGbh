# Wind Forecast Monitor

A web app that helps a UK utility's day-ahead trading team see the wind generation forecast that was available at auction time, and measure how accurate it was.

**Live app:** TODO (Vercel URL)
**Video walkthrough:** TODO (unlisted YouTube link)

## Repository layout

```
.
├── backend/                 FastAPI service (Python 3.12)
│   ├── main.py              App entrypoint; all routes under /api
│   ├── core/                Forecast selection and accuracy metrics
│   ├── data/                Cleaned Elexon data (parquet), bundled with the API
│   ├── tests/               pytest suite
│   ├── requirements.txt     Runtime dependencies
│   ├── requirements-dev.txt Test and ingestion dependencies
│   └── Dockerfile
├── frontend/                React + Vite (JavaScript), Tailwind, Recharts
│   ├── src/
│   ├── vite.config.js       Dev proxy: /api -> localhost:8000
│   ├── nginx.conf           Docker: serves the build, proxies /api -> backend
│   └── Dockerfile
├── scripts/ingest.py        One-off pull from the Elexon API into backend/data/
├── data/raw/                Raw API responses, kept for provenance (not deployed)
├── docker-compose.yml
└── vercel.json              Vercel Services config (frontend + backend in one project)
```

## Running the app

### With Docker (recommended)

```bash
docker compose up --build
```

Open http://localhost:8080. API docs are at http://localhost:8080/api/docs.

### Without Docker

```bash
# Terminal 1: backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Tests

```bash
cd backend && pytest
```

### Refreshing the data

The app reads pre ingested files and never calls Elexon at runtime. To rebuild them:

```bash
python scripts/ingest.py
```

## Deployment

Deployed on Vercel as a single project using Vercel Services. `vercel.json` defines two services: `frontend` (Vite) and `backend` (FastAPI). Requests to `/api/*` go to the backend and everything else to the frontend. The frontend always calls relative `/api` paths, so the same code works under the Vite dev proxy, nginx in Docker, and Vercel.

## Data and assumptions

TODO: data sources, scope (delivery days 2 Jan – 1 Feb 2026), decision cutoffs, hourly alignment of forecasts and actuals, observed forecast bias.

## Use of AI tools

TODO: describe how AI tools were used (required by the brief).
