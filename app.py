import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import sqlite3
import pandas as pd
import json, re
import os
from datetime import datetime

# =========================
# CONFIG
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
init_db()

st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")

# =========================
# STRIPE STYLE UI
# =========================
st.markdown("""
<style>
.block-container { padding-top: 2rem; max-width: 1200px; }

.metric-box {
    background: #f9fafb;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
}

.metric-label {
    font-size: 12px;
    color: #6b7280;
}

.metric-value {
    font-size: 26px;
    font-weight: 600;
    color: #111827;
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("📊 AI SaaS")

    user = st.text_input("Usuario").strip().lower()

    st.markdown("---")

    channels_input = st.text_area("Channel IDs")

    run_btn = st.button("🚀 Analizar")

# =========================
# MAIN
# =========================
st.title("📈 Intelligence Dashboard")

if not user:
    st.stop()

channels = [c.strip() for c in channels_input.split("\n") if c.strip()]
run_id = datetime.now().strftime("%Y%m%d%H%M%S")

# =========================
# RUN ANALYSIS
# =========================
if run_btn:

    for ch in channels:

        videos = get_videos(ch)

        for v in videos:

            prompt = f"""
Devuelve SOLO JSON:
{{
"sentimiento": "positivo|negativo|neutro",
"score": 0.0,
"resumen": "1 frase"
}}

Texto:
{v['title']} - {v['summary']}
"""

            res = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            text = res.choices[0].message.content
            match = re.search(r"\{.*\}", text, re.DOTALL)

            if match:
                data = json.loads(match.group())

                save_video(
                    user,
                    run_id,
                    ch,
                    v["title"],
                    data["sentimiento"],
                    float(data["score"]),
                    data["resumen"]
                )

    st.success(f"Run completado: {run_id}")

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
    st.warning("No hay datos aún")
    st.stop()

df["score"] = pd.to_numeric(df["score"], errors="coerce")

# =========================
# RUNS (FIX IMPORTANTE)
# =========================
runs = sorted(df["run_id"].dropna().unique(), reverse=True)

if len(runs) == 0:
    st.stop()

run_1 = runs[0]
run_2 = runs[1] if len(runs) > 1 else runs[0]

df1 = df[df["run_id"] == run_1]
df2 = df[df["run_id"] == run_2]

# =========================
# OVERVIEW (STRIPE STYLE)
# =========================
st.markdown("### 📊 Overview")

score_now = df1["score"].mean()
score_prev = df2["score"].mean()

if pd.isna(score_prev):
    score_prev = 0

delta = score_now - score_prev
delta_pct = (delta / (abs(score_prev) + 0.0001)) * 100

col1, col2, col3, col4 = st.columns(4)

col1.metric("Videos", len(df1), len(df1)-len(df2))
col2.metric("Score", round(score_now,2), f"{delta:+.2f} ({delta_pct:+.1f}%)")
col3.metric("Canales", df1["canal"].nunique(), df1["canal"].nunique()-df2["canal"].nunique())
col4.metric("Run", run_1[:8])

# =========================
# COMPARATIVA POR CANAL
# =========================
st.markdown("---")
st.subheader("📊 Channel Comparison")

r1 = df1.groupby("canal")["score"].mean()
r2 = df2.groupby("canal")["score"].mean()

compare = pd.DataFrame({
    "current": r1,
    "previous": r2
}).fillna(0)

compare["delta"] = compare["current"] - compare["previous"]

st.bar_chart(compare["delta"])

st.success(f"🏆 Best channel: {compare['delta'].idxmax()}")

# =========================
# SENTIMIENTO
# =========================
st.markdown("---")
st.subheader("📊 Sentiment")

st.bar_chart(df1["sentimiento"].value_counts())

# =========================
# TREND
# =========================
st.subheader("📈 Trend")

st.line_chart(df1["score"])