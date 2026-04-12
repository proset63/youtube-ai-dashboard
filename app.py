import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import json
import re
import pandas as pd
import sqlite3
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

init_db()

# 🎨 CONFIG UI
st.set_page_config(
    page_title="AI Analytics SaaS",
    layout="wide"
)

# 🧭 SIDEBAR (estilo empresa)
with st.sidebar:
    st.title("📊 AI SaaS Dashboard")

    user = st.text_input("Usuario")

    st.markdown("---")

    st.markdown("### 📥 Canales por industria")
    channels_input = st.text_area("Pega canales")

    run = st.button("🚀 Analizar")

# 🚫 STOP SIN USER
if not user:
    st.stop()

st.title("📈 Industry Intelligence Dashboard")

# 📦 PARSE CANALES
channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

# 🚀 ANALYSIS
if run:

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
                    channel_id,
                    v["title"],
                    data["sentimiento"],
                    float(data["score"]),
                    data["resumen"]
                )

    st.success("✅ Análisis completado")

# 📦 LOAD DATA
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
# 📊 KPI CARDS (TOP)
# =========================

col1, col2, col3, col4 = st.columns(4)

col1.metric("📹 Videos", len(df))
col2.metric("⭐ Score medio", round(df["score"].mean(), 2))
col3.metric("📡 Canales", df["canal"].nunique())
col4.metric("📊 Sentimiento positivo", (df["sentimiento"] == "positivo").sum())

st.markdown("---")

# =========================
# 📊 DASHBOARD PRINCIPAL
# =========================

left, right = st.columns(2)

with left:
    st.subheader("📊 Ranking de canales")
    ranking = df.groupby("canal")["score"].mean()
    st.bar_chart(ranking)

with right:
    st.subheader("📈 Evolución del score")
    st.line_chart(df["score"])

st.markdown("---")

# =========================
# 📊 ANALYTICS TABLES
# =========================

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Sentimiento por canal")
    st.dataframe(
        df.groupby(["canal", "sentimiento"]).size().unstack(fill_value=0)
    )

with col2:
    st.subheader("📊 Distribución global")
    st.bar_chart(df["sentimiento"].value_counts())

# =========================
# 🏆 INSIGHT BUSINESS
# =========================

st.markdown("---")
st.subheader("🧠 Insight automático")

if ranking.idxmax():
    st.success(f"🏆 Mejor canal: {ranking.idxmax()}")