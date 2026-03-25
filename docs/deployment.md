# Deployment

## Docker Compose (Production)

```bash
docker compose up --build
```

### Services

**backend**
- Build: `./Dockerfile`
- Base: `python:3.11-slim`
- System deps: `build-essential`, `libpango-1.0-0`, `libpangoft2-1.0-0` (WeasyPrint)
- Port: `8000:8000`
- Volume: `./data:/app/data` (persistent storage)
- Env: `.env` file
- CMD: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

**frontend**
- Build: `./frontend/Dockerfile`
- Multi-stage: deps → builder → runner (Node 20 alpine)
- Build-time env: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Port: `3000:3000`
- Output: Next.js standalone mode
- User: `nextjs` (uid 1001)
- CMD: `node server.js`
- Depends on: backend

### Data Persistence

The `data/` volume is the only stateful component. It contains:
- User profile, notifications
- All artifacts, task logs, conversation sessions, goals
- LangGraph checkpoints (SQLite)
- Memory distiller output
- Web scraper cache

Back up `./data/` for full state preservation.

## Local Development

### Backend
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend expects backend at `http://localhost:8001` (hardcoded in `useAppStore.ts` as `API_BASE`).

Docker frontend expects backend at `http://localhost:8000` (set at build time via `NEXT_PUBLIC_API_URL`).

## Environment Variables

Required in `.env`:
```
GEMINI_API_KEY=...     # Google Generative AI API key
TAVILY_API_KEY=...     # Tavily search API key
```

Copy from `.env.example`:
```bash
cp .env.example .env
```

## Startup Behavior

On backend startup (`api/main.py` lifespan):
1. Creates directory tree: `data/{career,life,learning}/{artifacts,logs}`, `data/checkpoints`
2. Initializes `ProactiveScheduler` (APScheduler)
3. `TaskManager` singleton cancels any stale running tasks

On shutdown:
1. Gracefully stops scheduler

## Port Configuration

| Service | Dev Port | Docker Port |
|---------|----------|-------------|
| Backend | 8001 | 8000 |
| Frontend | 3000 | 3000 |

## CORS

Backend allows: `http://localhost:3000`, `http://127.0.0.1:3000`

If deploying behind a reverse proxy or on a different domain, update CORS origins in `api/main.py`.

## System Dependencies

WeasyPrint requires system-level libraries:
- Debian/Ubuntu: `libpango-1.0-0 libpangoft2-1.0-0`
- macOS: `brew install pango`
- Already included in Dockerfile

## Build Artifacts

- Backend: No build step (runs directly with uvicorn)
- Frontend: `npm run build` produces `.next/standalone/` directory
- Docker frontend copies standalone output to final image
