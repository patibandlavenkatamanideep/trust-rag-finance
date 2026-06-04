"""TrustRAG Finance — friendly, non-technical UI.

Designed so a wealth advisor (not an engineer) immediately understands what the
tool does: ask a research question, get an answer where every fact is cited, and
trust that it says "I couldn't find that" instead of guessing.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.environ.get("TRUSTRAG_API_URL", "http://localhost:8000")

st.set_page_config(page_title="TrustRAG Finance", page_icon="📊", layout="wide")

# --------------------------------------------------------------------------- #
# Styling — clean cards, chips, and step blocks.
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
      .hero {background:#0f1722; border:1px solid #1e2a3a; border-radius:16px;
             padding:28px 32px; margin-bottom:8px;}
      .hero h1 {color:#fff; font-size:32px; margin:0 0 8px 0; line-height:1.25;}
      .hero p {color:#9fb0c3; font-size:16px; margin:0 0 16px 0; line-height:1.5;}
      .chip {display:inline-block; background:#15202e; border:1px solid #25344a;
             color:#cdd9e6; border-radius:999px; padding:6px 14px; margin:4px 6px 0 0;
             font-size:13px;}
      .step {padding:6px 0;}
      .stepnum {display:inline-block; width:24px; height:24px; line-height:24px;
                text-align:center; border-radius:50%; background:#2563eb; color:#fff;
                font-size:13px; margin-right:8px;}
      .band {border-radius:12px; padding:14px 18px; font-size:16px; margin:6px 0 14px 0;}
      .band-high {background:#0f2a17; border:1px solid #1f7a3d; color:#7ee2a3;}
      .band-medium {background:#2a2410; border:1px solid #7a6a1f; color:#e6d27e;}
      .band-low {background:#2a1810; border:1px solid #7a4a1f; color:#e6a87e;}
      .band-abstain {background:#1a1f27; border:1px solid #38465a; color:#9fb0c3;}
      .src {background:#0f1722; border:1px solid #1e2a3a; border-radius:10px;
            padding:10px 14px; margin:6px 0; color:#cdd9e6;}
      .src small {color:#7d8ea3;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### 📊 TrustRAG Finance")
    st.caption("Research answers you can trust")
    st.markdown("---")
    st.markdown("**What makes it different**")
    st.markdown(
        "- Every fact is **cited** to a source\n"
        "- It **says \"I don't know\"** instead of guessing\n"
        "- It won't give **personal buy/sell advice**\n"
        "- Each answer gets a **trust rating**"
    )
    st.markdown("---")
    st.caption(
        "Independent educational project. Not affiliated with Morgan Stanley or "
        "OpenAI. Not investment advice."
    )

# --------------------------------------------------------------------------- #
# Hero
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="hero">
      <h1>Ask about company research — get answers you can trust</h1>
      <p>Type a question about a company's filings. You get a clear answer where
         <b>every fact is backed by a source</b> — and if the research doesn't cover
         your question, it tells you honestly instead of making something up.</p>
      <span class="chip">✓ Every answer cited</span>
      <span class="chip">✓ Says "I couldn't find that"</span>
      <span class="chip">✓ No made-up facts</span>
      <span class="chip">✓ Trust rating on every answer</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Ask box + examples + how-it-works
# --------------------------------------------------------------------------- #
left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("#### Ask a question")
    query = st.text_input(
        "question", key="query", label_visibility="collapsed",
        placeholder="e.g. What does Apple say about services revenue?",
    )
    ask = st.button("Ask", type="primary")

    st.markdown("**Or try an example:**")
    examples = [
        ("🍏 Apple — services revenue", "What does Apple say about services revenue?"),
        ("🎮 NVIDIA — key risks", "What are NVIDIA's key risk factors?"),
        ("🚫 Out of scope", "What does Apple say about its quantum computing division?"),
        ("⚖️ Advice (should refuse)", "Should I tell my client to buy Nvidia?"),
    ]
    ecols = st.columns(2)
    for i, (label, q) in enumerate(examples):
        if ecols[i % 2].button(label, use_container_width=True, key=f"ex_{i}"):
            st.session_state["pending"] = q
            ask = True

with right:
    st.markdown("#### How it works")
    steps = [
        ("You ask", "Type a plain-English question about the research."),
        ("It finds sources", "Searches the company filings for the most relevant passages."),
        ("It checks every fact", "Confirms each statement is actually backed by a source."),
        ("You get a trust rating", "High, medium, or \"couldn't find it\" — never a confident guess."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(
            f'<div class="step"><span class="stepnum">{i}</span><b>{title}</b><br>'
            f'<span style="color:#7d8ea3; margin-left:32px;">{desc}</span></div>',
            unsafe_allow_html=True,
        )

# An example button sets a pending question; use it for this run.
if st.session_state.get("pending"):
    query = st.session_state.pop("pending")

# --------------------------------------------------------------------------- #
# Run query
# --------------------------------------------------------------------------- #
if ask and query:
    with st.spinner("Reading the research..."):
        try:
            resp = requests.post(f"{API_URL}/query", json={"query": query}, timeout=90)
            resp.raise_for_status()
            st.session_state["last"] = resp.json()
            st.session_state["last_q"] = query
        except Exception as exc:  # noqa: BLE001
            st.error(f"Couldn't reach the service: {exc}")

# --------------------------------------------------------------------------- #
# Result
# --------------------------------------------------------------------------- #
if "last" in st.session_state:
    data = st.session_state["last"]
    band = data["confidence"]["band"]
    st.markdown("---")
    st.markdown(f"#### Answer to: *{st.session_state.get('last_q','')}*")

    band_copy = {
        "high": ("✓ High confidence", "Every fact below is backed by a source."),
        "medium": ("Please double-check the sources", "The answer is supported, but worth a quick verify."),
        "low": ("Low confidence — verify carefully", "Evidence is thin; treat this as a lead, not a fact."),
        "abstain": ("Couldn't answer from the research", "The filings don't cover this — so it won't guess."),
    }
    title, sub = band_copy.get(band, (band, ""))
    st.markdown(
        f'<div class="band band-{band}"><b>{title}</b><br>'
        f'<span style="opacity:.85">{sub}</span></div>',
        unsafe_allow_html=True,
    )

    if data.get("abstained"):
        st.info(f"💬 {data['answer']}")
    else:
        st.write(data["answer"])

        claims = data.get("claims", [])
        if claims:
            st.markdown("**What it told you — and where each part comes from:**")
            for c in claims:
                tag = ", ".join(c.get("source_ids", [])) or "—"
                st.markdown(
                    f"- ✓ {c['text']} &nbsp;<small style='color:#7d8ea3'>({tag})</small>",
                    unsafe_allow_html=True,
                )

        sources = data.get("retrieved_sources", [])
        if sources:
            with st.expander(f"📄 See the {len(sources)} source passage(s)"):
                for s in sources:
                    meta = " · ".join(
                        str(x) for x in [
                            s.get("company") or s.get("ticker"),
                            s.get("section"),
                            f"page {s['page']}" if s.get("page") else None,
                        ] if x
                    )
                    st.markdown(
                        f'<div class="src"><b>[{s["source_id"]}]</b> {s["document_title"]}'
                        f'<br><small>{meta}</small><br>{s["text"][:400]}</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("**Was this helpful?**")
    fcols = st.columns(4)
    for col, (label, verdict) in zip(
        fcols,
        [("👍 Used as-is", "used_as_is"), ("✏️ Edited", "edited"),
         ("👎 Rejected", "rejected"), ("⚠️ Disputed", "disputed")],
    ):
        if col.button(label, use_container_width=True, key=f"fb_{verdict}"):
            try:
                requests.post(
                    f"{API_URL}/feedback",
                    json={"query_id": data["query_id"], "verdict": verdict}, timeout=30,
                )
                st.success("Thanks — recorded.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Couldn't record: {exc}")
