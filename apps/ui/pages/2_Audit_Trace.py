"""Audit trace view — provenance + tamper-evidence.

Shows the hash-chained audit ledger: each query's retrieved chunks, citations,
confidence, model/prompt version, and the chain-integrity check. "You can't
defend 'the AI decided' in court" — this is the explainability/audit surface.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.environ.get("TRUSTRAG_API_URL", "http://localhost:8000")

st.set_page_config(page_title="TrustRAG Audit Trace", page_icon="🔐", layout="wide")
st.title("🔐 Audit Trace")
st.caption("Append-only, hash-chained ledger. Every query's provenance is logged and tamper-evident.")


def _get(path: str, **params):
    return requests.get(f"{API_URL}{path}", params=params, timeout=30).json()


try:
    integrity = _get("/audit/verify")
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not reach API at {API_URL}: {exc}")
    st.stop()

valid = integrity.get("valid")
if valid is True:
    st.success(f"✅ Chain intact — {integrity.get('rows', 0)} entries · head {str(integrity.get('head_hash',''))[:16]}…")
elif valid is False:
    st.error(f"❌ TAMPER DETECTED — chain breaks at seq {integrity.get('broken_at_seq')} "
             f"(query {integrity.get('broken_query_id')})")
else:
    st.info(integrity.get("detail", "Audit store is not a hash-chained ledger."))

st.subheader("Recent ledger entries")
try:
    recent = _get("/audit/recent", limit=50)
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to load entries: {exc}")
    st.stop()

records = recent.get("records", [])
if not records:
    st.info("No audit entries yet — run a query from the main page first.")
    st.stop()

for r in records:
    if r.get("type") == "feedback":
        st.markdown(f"**💬 feedback** on `{r.get('ref_query_id','')[:8]}` → "
                    f"{r.get('verdict')} {('· ' + r['note']) if r.get('note') else ''}")
        continue
    band = r.get("confidence_band", "?")
    with st.expander(f"[{band.upper()}] {r.get('user_query','')[:70]}  ·  {r.get('query_id','')[:8]}"):
        st.write(f"**Model:** {r.get('model_name')} · **Prompt:** {r.get('prompt_version')} "
                 f"· **Latency:** {r.get('latency_ms')}ms")
        st.write(f"**Confidence:** {band} — {r.get('confidence_reason','')}")
        st.write(f"**Retrieved chunks:** {', '.join(r.get('retrieved_chunk_ids', [])) or 'none'}")
        cites = r.get("citations", [])
        if cites:
            st.write("**Citations:**")
            st.json(cites)
        ver = r.get("citation_verification", {})
        st.write(f"**Citation validity:** {ver.get('citation_validity')} · "
                 f"**Groundedness:** {r.get('groundedness_result', {}).get('score')}")
