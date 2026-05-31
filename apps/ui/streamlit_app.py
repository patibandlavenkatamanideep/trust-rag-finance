"""HITL verification widget (Streamlit).

Surfaces the answer, confidence band, per-claim citation status, source
snippets, and feedback buttons. The goal (Human-Factors, S9): make verifying
easier than blind trust. Talks to the API over HTTP.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.environ.get("TRUSTRAG_API_URL", "http://localhost:8000")

BAND_COLOR = {"high": "🟢", "medium": "🟡", "low": "🟠", "abstain": "⚪"}

st.set_page_config(page_title="TrustRAG Finance", page_icon="📊", layout="wide")
st.title("📊 TrustRAG Finance — Advisor Research Assistant")
st.caption(
    "Read-only. No personalized advice. Every claim is cited or the system abstains. "
    "Independent portfolio project — not affiliated with Morgan Stanley or OpenAI."
)

query = st.text_input("Ask a research question", placeholder="What does Apple say about services revenue?")

if st.button("Ask", type="primary") and query:
    try:
        resp = requests.post(f"{API_URL}/query", json={"query": query}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 - surface error, don't hide it
        st.error(f"Request failed: {exc}")
        st.stop()

    st.session_state["last"] = data

if "last" in st.session_state:
    data = st.session_state["last"]
    conf = data["confidence"]
    band = conf["band"]

    st.subheader(f"{BAND_COLOR.get(band, '⚪')} Confidence: {band.upper()}")
    st.write(conf.get("reason", ""))

    if band in ("medium", "low"):
        st.warning("⚠️ Verify these sources before relying on this answer.")
    if data.get("abstained"):
        st.info("The system abstained — it could not ground an answer in the corpus.")

    st.markdown("### Answer")
    st.write(data["answer"] or "_(abstained)_")

    if data.get("claims"):
        st.markdown("### Claims & citation status")
        for c in data["claims"]:
            mark = "✅" if c.get("supported") else "❌"
            st.write(f"{mark} {c['text']}  \n— sources: {', '.join(c.get('source_ids', [])) or 'none'}")

    if data.get("retrieved_sources"):
        st.markdown("### Source passages")
        for s in data["retrieved_sources"]:
            with st.expander(f"[{s['source_id']}] {s['document_title']} — {s.get('section') or ''} p.{s.get('page')}"):
                st.write(s["text"])

    st.markdown("### Your verdict")
    cols = st.columns(4)
    verdicts = ["used_as_is", "edited", "rejected", "disputed"]
    for col, verdict in zip(cols, verdicts):
        if col.button(verdict.replace("_", " ").title()):
            try:
                requests.post(
                    f"{API_URL}/feedback",
                    json={"query_id": data["query_id"], "verdict": verdict},
                    timeout=30,
                )
                st.success(f"Recorded: {verdict}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Feedback failed: {exc}")
