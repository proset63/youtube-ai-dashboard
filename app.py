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
# SIDEBAR (UI PRO)
# =========================
with st.sidebar:
    st.title("📊 AI SaaS Dashboard")

    user = st.text_input("Usuario")

    st.markdown("---")

    st.subheader("📥 Canales")
    channels_input = st.text_area("Channel IDs (uno por línea)")

    run_button = st.button("🚀 Analizar")

    st.markdown("---")

    st.subheader("🧠 Info")
    st.caption("Cada análisis = 1 run independiente")

# =========================
# MAIN
# =========================
st.title("📈 Industry Intelligence Dashboard")

if not user:
    st.stop()

# =========================
# PARSE CHANNELS
# =========================
channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

# =========================
# RUN ID
# =========================
run_id = datetime.now().strftime("%Y%m%d%H%M%S")

# =========================
# ANALYSIS
# =========================
if run_button:

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
# KPI DASHBOARD
# =========================
st.markdown("## 📊 KPIs")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Videos (actual)", len(df1))
c2.metric("Score medio", round(df1["score"].mean(), 2))
c3.metric("Canales", df1["canal"].nunique())
c4.metric("Run ID", run_1)

st.markdown("---")

# =========================
# COMPARACIÓN RUNS
# =========================
st.subheader("📊 Comparación de runs")

score1 = df1["score"].mean()
score2 = df2["score"].mean()

delta = score1 - score2

a, b, c = st.columns(3)

a.metric("Score actual", round(score1, 2))
b.metric("Score anterior", round(score2, 2))
c.metric("Cambio", round(delta, 2))

st.markdown("---")

# =========================
# POR CANAL
# =========================
st.subheader("📊 Evolución por canal")

r1 = df1.groupby("canal")["score"].mean()
r2 = df2.groupby("canal")["score"].mean()

compare = pd.DataFrame({
    "actual": r1,
    "anterior": r2
}).fillna(0)

compare["delta"] = compare["actual"] - compare["anterior"]

st.dataframe(compare)
st.bar_chart(compare["delta"])

st.success(f"🏆 Mejor evolución: {compare['delta'].idxmax()}")

# =========================
# SENTIMIENTO
# =========================
st.subheader("📊 Sentimiento actual")
st.bar_chart(df1["sentimiento"].value_counts())

# =========================
# EVOLUCIÓN
# =========================
st.subheader("📈 Evolución del score")
st.line_chart(df1["score"])