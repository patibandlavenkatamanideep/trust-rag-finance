"""Eval dashboard — 'here's how the RAG system performs'.

Renders the latest golden-set eval: the 7 deploy metrics vs their bars, the
overall deploy gate, and a per-category breakdown. The portfolio-critical view —
most people show a RAG demo; few show the scoreboard.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.environ.get("TRUSTRAG_API_URL", "http://localhost:8000")

st.set_page_config(page_title="TrustRAG Eval Dashboard", page_icon="📈", layout="wide")
st.title("📈 Eval Dashboard")
st.caption("Groundedness-first evaluation. The kill metric is false-confident answers.")

col_run, col_mode = st.columns([1, 3])
with col_run:
    run = st.button("Run eval", type="primary")
with col_mode:
    live = st.toggle("Use live LLM (costs API)", value=False)

if run:
    with st.spinner("Running golden-set eval..."):
        try:
            requests.post(f"{API_URL}/eval/run", params={"live": str(live).lower()}, timeout=300)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Run failed: {exc}")

try:
    data = requests.get(f"{API_URL}/eval/results", timeout=30).json()
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not reach API at {API_URL}: {exc}")
    st.stop()

bars = {b["name"]: b for b in data.get("deploy_bars", [])}
latest = data.get("latest_run")
st.write(f"Golden set: **{data.get('golden_size', 0)}** questions")

if not latest:
    st.info("No eval has been run yet. Click **Run eval** (or run `python scripts/run_eval.py`).")
    st.stop()

metrics = latest["metrics"]
deploy_ok = latest.get("deploy_ok")
mode = latest.get("mode", "?")

st.subheader(("✅ DEPLOY GATE: PASS" if deploy_ok else "❌ DEPLOY GATE: FAIL") + f"  ·  mode: {mode}")

# Metric cards vs bars.
order = ["groundedness", "false_confident_rate", "citation_validity", "recall_at_10",
         "correctness", "abstention_precision", "hallucination_rate"]
gate = latest.get("gate", {})
cols = st.columns(4)
for i, name in enumerate(order):
    if name not in metrics:
        continue
    b = bars.get(name, {})
    passed = gate.get(name)
    label = name.replace("_", " ")
    delta = f"{'✅' if passed else '❌'} bar {b.get('direction','')}:{b.get('bar','')}"
    cols[i % 4].metric(label, metrics[name], delta, delta_color="off" if passed else "inverse")

st.metric("avg latency (ms)", metrics.get("avg_latency_ms"))

# Per-category breakdown.
st.subheader("By category")
by_cat = latest.get("by_category", {})
rows = [
    {"category": c, "n": v["n"], "correct": v["correct"], "false_confident": v["false_confident"]}
    for c, v in by_cat.items()
]
if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)

# Per-question detail.
with st.expander("Per-question detail"):
    st.dataframe(latest.get("questions", []), use_container_width=True, hide_index=True)
