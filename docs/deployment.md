# Deployment (Railway)

TrustRAG Finance deploys cleanly on Railway. The API is the primary service; the
Streamlit UI is an optional second service.

## API service (primary)

`railway.json` configures the API to build from `apps/api/Dockerfile` and start
with Railway's injected `$PORT`. The Dockerfile installs the monorepo
(`pip install .`) and copies `data/` so the demo corpus ships in the image.

**Steps:**
1. Create a Railway project → **Deploy from GitHub repo** → select this repo.
2. Railway reads `railway.json` (Dockerfile build, start command, `/health` check).
3. Set **Variables** (Railway dashboard → Variables):
   ```
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-2.5-flash
   GEMINI_API_KEY=<your key>     # secret — set here, NEVER in the repo
   AUTO_INGEST=1                  # self-seed the corpus on boot (default on)
   ```
   Leave `LLM_PROVIDER=stub` if you want a keyless deploy (extractive synthesizer).
4. Deploy. On boot the API self-seeds the SQLite index from `data/sample_docs`
   (the startup hook in `app/main.py`), so `/query` works immediately.
5. Verify: `GET https://<your-app>.up.railway.app/health` and `/docs`.

## UI service (optional, second service)

Add a **second service** in the same Railway project from the same repo:
- **Build**: Dockerfile, path `apps/ui/Dockerfile`.
- **Start**: `streamlit run apps/ui/streamlit_app.py --server.address=0.0.0.0 --server.port=$PORT`
- **Variables**: `TRUSTRAG_API_URL=https://<your-api-service>.up.railway.app`

(Railway sets a per-service Dockerfile path + start command in the service
settings, since one repo can back multiple services.)

## Persistence (filesystem is ephemeral)

Railway's container filesystem resets on each deploy. Two options:

- **Demo (default):** `AUTO_INGEST=1` re-ingests `data/sample_docs` on every boot.
  Stateless and fine for a portfolio demo.
- **Persistent index:** attach a **Railway Volume** mounted at `data/index/`, so the
  SQLite ChunkStore survives redeploys.
- **Production path:** swap the `ChunkStore` seam for **Railway Postgres + pgvector**
  (an adapter swap behind `shared.interfaces.ChunkStore` — no pipeline changes).
  Set `DATABASE_URL` from the Railway Postgres plugin.

## Notes

- The macOS `.pth` import quirk does NOT affect Railway (Linux path, no space); the
  Docker image uses a normal `pip install .`, and `app/__init__.py` bootstraps paths
  as a belt-and-suspenders.
- Cost: with `LLM_PROVIDER=gemini` each `/query` makes one Gemini call (~seconds,
  low cost on flash). Use `stub` for a zero-cost keyless deploy.
- The audit store is in-memory (per-process). For durable audit across restarts,
  implement the Postgres `AuditStore` adapter (seam already defined, D28).
