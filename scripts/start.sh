#!/usr/bin/env bash
# Combined launcher for Railway: one service serves the Streamlit UI publicly on
# $PORT, with the FastAPI backend running internally on 127.0.0.1:8000. The UI
# talks to the API over localhost. This gives a single always-live public URL.
set -euo pipefail

export AUTO_INGEST="${AUTO_INGEST:-1}"          # seed the corpus on boot
export TRUSTRAG_API_URL="http://127.0.0.1:8000" # UI -> internal API
PORT="${PORT:-8501}"                            # Railway injects $PORT

echo "[start] launching API on internal :8000 ..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir apps/api &

echo "[start] waiting for API health ..."
python - <<'PY'
import time, urllib.request
for _ in range(90):
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
        print("[start] API healthy"); break
    except Exception:
        time.sleep(1)
else:
    print("[start] WARNING: API not healthy yet — starting UI anyway")
PY

echo "[start] launching Streamlit UI on public :$PORT ..."
exec streamlit run apps/ui/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --browser.gatherUsageStats=false
