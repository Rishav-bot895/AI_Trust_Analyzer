# AI Trust Analyzer

Full-stack factuality-risk analysis tool with a FastAPI backend and Next.js frontend.

## Prerequisites

- Python 3.14.2 for the backend virtual environment
- Node.js 20+ and npm
- Supabase PostgreSQL with pgvector enabled

## Local Setup

### 1. Create Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use this interpreter for backend commands:

```text
.\.venv\Scripts\python.exe
```

### 2. Configure backend environment

Copy `backend\.env.example` to `backend\.env` and fill in the required values.

### 3. Install frontend dependencies

```powershell
cd frontend
npm install
```

### 4. Start backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

### 5. Start frontend

From `frontend`:

```powershell
npm run dev
```

Frontend runs at `http://localhost:3000`.

## Environment Variables

Backend variables live in `backend/.env`.

| Variable | Required | Default | Service | Description |
| --- | --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | none | Backend | Gemini API key for internal analysis agents. |
| `TAVILY_API_KEY` | Yes | none | Backend | Tavily API key for web retrieval. |
| `ENVIRONMENT` | No | `development` | Backend | Runtime environment: `development`, `production`, or `test`. |
| `DATABASE_URL` | Yes | none | Backend | SQLAlchemy URL. Use `postgresql+asyncpg://...` for Supabase/PostgreSQL. |
| `SUPABASE_URL` | Yes | none | Backend | Supabase project URL, used for JWKS resolution. |
| `SUPABASE_ANON_KEY` | Yes | none | Backend/Frontend future auth | Supabase anon key. Required by backend settings. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | none | Backend | Service role key for protected cleanup endpoints. |
| `SUPABASE_JWT_SECRET` | Yes | none | Backend | JWT secret for guest-session signing and HS256 fallback. |
| `SUPABASE_JWT_VERIFY_STRATEGY` | No | `jwks` | Backend | Use `jwks` in production; `hs256` is useful for tests/dev. |
| `SUPABASE_JWT_ISSUER` | No | empty | Backend | Optional issuer claim validation. |
| `SUPABASE_JWT_AUDIENCE` | No | empty | Backend | Optional audience claim validation. |
| `SUPABASE_JWKS_URL` | No | derived | Backend | Optional explicit JWKS URL override. |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000"]` | Backend | CORS origins as JSON array or comma-separated string. |
| `LOG_LEVEL` | No | `INFO` | Backend | Application log level. |
| `MAX_CLAIMS` | No | `50` | Backend | Maximum extracted claims per analysis. |
| `VECTOR_EMBEDDING_DIM` | No | `384` | Backend | pgvector embedding dimension. |
| `GUEST_SESSION_TTL_HOURS` | No | `24` | Backend | Guest retention window. |
| `NEXT_PUBLIC_API_URL` | Yes in production | `http://localhost:8000` | Frontend | Public backend URL used by browser requests. |

Frontend variables live in `frontend/.env` or the Vercel project settings.

## Docker

Build the backend image:

```powershell
docker build -t ai-trust-backend ./backend
```

Run the backend container:

```powershell
docker run --rm --env-file backend/.env -p 8000:8000 ai-trust-backend
```

Start backend and frontend together:

```powershell
docker compose up --build
```

## Deployment

### Backend on Render

No `render.yaml` is included because deployment is configured manually in the Render website.

Recommended Render settings:

| Setting | Value |
| --- | --- |
| Runtime | Docker |
| Root directory | `backend` |
| Dockerfile path | `backend/Dockerfile` if root is repository root, or `Dockerfile` if root is `backend` |
| Health check path | `/api/v1/health` |
| Port binding | The Dockerfile runs `python -m app.start`, which starts Uvicorn with Render's `PORT`; local Docker defaults to `8000`. |
| Python version note | Local venv uses Python 3.14.2; Docker image uses `python:3.14.2-slim`. |

Leave Render's Start Command blank when using the Docker runtime so the Dockerfile `CMD` runs. If you do override it, use:

```sh
python -m app.start
```

Set all backend environment variables from the table above in Render. Do not commit secrets.

### Frontend on Vercel

Use `frontend` as the Vercel project root.

Set:

```text
NEXT_PUBLIC_API_URL=https://your-render-backend.onrender.com
```

Update `frontend/vercel.json` so the rewrite destination points to your real Render backend URL.

## CI

GitHub Actions workflow is in `.github/workflows/ci.yml`.

It runs:

- Backend tests with Python 3.14.2
- Frontend lint
- Frontend production build
- Frontend unit tests

## Useful Commands

Backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
npm test -- --run
```
