# Deployment (Railway)

TrustRAG Finance deploys as a **single combined service**: one container runs the
Streamlit **UI publicly** on Railway's `$PORT`, with the FastAPI **backend
internally** on `127.0.0.1:8000`. You get one always-live public URL (the UI),
and the UI talks to the API over localhost.

Live: https://trust-rag-finance-production.up.railway.app/

## How it's wired

- `Dockerfile` (repo root) installs the monorepo + UI extra (`pip install ".[ui]"`)
  and copies `data/` so the demo corpus ships in the image.
- `scripts/start.sh` launches `uvicorn` (internal :8000), waits for `/health`, then
  `exec`s `streamlit` on `0.0.0.0:$PORT`. The UI reads `TRUSTRAG_API_URL=http://127.0.0.1:8000`.
- `railway.json` builds from the root `Dockerfile` and health-checks `/_stcore/health`
  (Streamlit's health endpoint).

## Deploy steps

1. Push to GitHub (Railway auto-redeploys on push).
2. In the Railway service, make sure it builds from the repo root `Dockerfile`
   (this is what `railway.json` specifies; no manual start command needed).
3. Set **Variables** (Railway dashboard → Variables):
   ```
   LLM_PROVIDER=gemini            # or 'stub' for a keyless, instant, extractive demo
   LLM_MODEL=gemini-2.5-flash
   GEMINI_API_KEY=<your key>      # secret — set here, NEVER in the repo
   AUTO_INGEST=1                  # self-seed the corpus on boot (default on)
   ```
   `PORT` is injected by Railway automatically — do **not** set it.
4. Deploy. On boot the API self-seeds the SQLite index from `data/sample_docs`
   (startup hook in `app/main.py`); the UI comes up once the API is healthy.
5. Open `https://<your-app>.up.railway.app/` → the Streamlit UI.

## Speed vs. realism

- `LLM_PROVIDER=stub` → instant answers (extractive synthesizer), zero API cost.
- `LLM_PROVIDER=gemini` → real synthesized answers (~7s/query on flash, low cost).
  Recommended for the demo video; switch to `stub` if you want snappy clicks.

## Persistence (filesystem is ephemeral)

Railway's container filesystem resets on each deploy. Options:

- **Demo (default):** `AUTO_INGEST=1` re-ingests `data/sample_docs` on every boot.
  Stateless and fine for a portfolio demo.
- **Persistent index/audit:** attach a **Railway Volume** mounted at `data/index/`
  so the SQLite ChunkStore + hash-chained audit ledger survive redeploys.
- **Production path:** swap the `ChunkStore` / `AuditStore` seams for **Railway
  Postgres (+ pgvector)** — adapter swaps behind `shared.interfaces`, no pipeline
  changes. Set `DATABASE_URL` from the Railway Postgres plugin.

## Exposing the API publicly too (optional)

The combined service keeps the API internal. If you also want public `/docs` and
`/query` (e.g. for the API portfolio story), add a **second Railway service** from
the same repo that builds from `apps/api/Dockerfile` — it serves the API on its own
public URL. The UI does not need it (it uses the internal API).

## Notes

- The macOS `.pth` import quirk and the ~minutes-long first-import lib scan do NOT
  affect Railway (Linux, no space in path, normal `pip install`).
- The hash-chained audit ledger is durable within a container run; use a Volume or
  Postgres for cross-restart durability.
