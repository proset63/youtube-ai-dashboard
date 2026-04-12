import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import json
import re
import pandas as pd
import sqlite3
import os
from datetime import datetime

# =========================
# CONFIG
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
init_db()

st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")

# =========================
# STRIPE STYLE CSS
# =========================
st.markdown("""
<style>
.metric-card {
    background: #f9fafb;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
}

.metric-label {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 6px;
}

.metric-value {
    font-size: 26px;
    font-weight: 600;
    color: #111827;
}

.metric-delta-up {
    color: #16a34a;
    font-size: 12px;
}

.metric-delta-down {
    color: #dc2626;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("📊 Analytics SaaS")

    user = st.text_input("Usuario")

    st.markdown("---")

    channels_input = st.text_area("Channel IDs")

    run_btn = st.button("🚀 Analizar")

    st.caption("Cada análisis = snapshot (run)")

# =========================
# MAIN
# =========================
st.title("📈 Industry Intelligence Dashboard")

if not user:
    st.stop()

channels = [c.strip() for c in channels_input.split("\n") if c.strip()]
run_id = datetime.now().strftime("%Y%m%d%H%M%S")

# =========================
# RUN ANALYSIS
# =========================
if run_btn:

    for channel_id in channels:

        videos = get_videos(channel_id)

        for v in videos:

            prompt = f"""
Devuelve SOLO JSON:
{{
  "sentimiento": "positivo | negativo | neutro",
  "score": 0.0,
  "resumen": "1 frase"
}}

Texto:
{v['title']} - {v['summary']}
"""

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            result = response.choices[0].message.content
            match = re.search(r"\{.*\}", result, re.DOTALL)

            if match:
                data = json.loads(match.group())

                save_video(
                    user,
                    run_id,
                    channel_id,
                    v["title"],
                    data["sentimiento"],
                    float(data["score"]),
                    data["resumen"]
                )

    st.success(f"✅ Run completado: {run_id}")

# =========================
# LOAD DATA
# =========================
conn = sqlite3.connect("data.db")

df = pd.read_sql_query(
    "SELECT * FROM videos WHERE user=?",
    conn,
    params=(user,)
)

if df.empty:
    st.warning("⚠️ No hay datos aún")
    st.stop()

df["score"] = pd.to_numeric(df["score"], errors="coerce")

# =========================
# RUN SELECTOR
# =========================
runs = sorted(df["run_id"].unique(), reverse=True)

col1, col2 = st.columns(2)

with col1:
    run_1 = st.selectbox("Run actual", runs)

with col2:
    run_2 = st.selectbox("Run anterior", runs)

df1 = df[df["run_id"] == run_1]
df2 = df[df["run_id"] == run_2]

# =========================
# STRIPE METRICS
# =========================
st.markdown("### 📊 Overview")

score_now = df1["score"].mean()
score_prev = df2["score"].mean()

delta = score_now - score_prev
delta_pct = (delta / (abs(score_prev) + 0.0001)) * 100

videos_delta = len(df1) - len(df2)
channels_delta = df1["canal"].nunique() - df2["canal"].nunique()

col1, col2, col3, col4 = st.columns(4)

def metric_card(label, value, delta_text, positive=True):
    color_class = "metric-delta-up" if positive else "metric-delta-down"

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="{color_class}">{delta_text}</div>
    </div>
    """, unsafe_allow_html=True)

with col1:
    metric_card(
        "Videos",
        len(df1),
        f"{videos_delta:+d} vs prev",
        videos_delta >= 0
    )

with col2:
    metric_card(
        "Avg Score",
        f"{score_now:.2f}",
        f"{delta:+.2f} ({delta_pct:+.1f}%)",
        delta >= 0
    )

with col3:
    metric_card(
        "Channels",
        df1["canal"].nunique(),
        f"{channels_delta:+d} vs prev",
        channels_delta >= 0
    )

with col4:
    metric_card(
        "Run",
        run_1[:8],
        "current snapshot",
        True
    )

# =========================
# COMPARISON
# =========================
st.markdown("---")
st.subheader("📊 Channel Performance")

r1 = df1.groupby("canal")["score"].mean()
r2 = df2.groupby("canal")["score"].mean()

compare = pd.DataFrame({
    "current": r1,
    "previous": r2
}).fillna(0)

compare["delta"] = compare["current"] - compare["previous"]

st.bar_chart(compare["delta"])

st.success(f"🏆 Best improvement: {compare['delta'].idxmax()}")

# =========================
# SENTIMENT
# =========================
st.markdown("---")
st.subheader("📊 Sentiment")

st.bar_chart(df1["sentimiento"].value_counts())

# =========================
# TREND
# =========================
st.subheader("📈 Trend")

st.line_chart(df1["score"])