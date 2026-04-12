import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import json
import re
import pandas as pd
import sqlite3
import os

# 🔐 OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

init_db()

# 🎨 UI CONFIG
st.set_page_config(
    page_title="AI SaaS Dashboard",
    layout="wide"
)

st.title("📊 AI Industry Intelligence Dashboard")

# 👤 USER
user = st.text_input("Usuario")

if not user:
    st.stop()

st.success(f"Bienvenido {user} 👋")

# 📥 INPUT CANALES
st.subheader("📥 Canales a analizar")

channels_input = st.text_area("Pega Channel IDs (uno por línea)")
channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

run = st.button("🚀 Analizar")

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

# 🚨 SI NO HAY DATOS
if df.empty:
    st.warning("⚠️ No hay datos todavía")
    st.stop()

# 🔢 CLEAN
df["score"] = pd.to_numeric(df["score"], errors="coerce")

# 🚨 CLAVE: SOLO CANALES ACTUALES
df = df[df["canal"].isin(channels)]

# =========================
# 📊 KPI CARDS
# =========================

col1, col2, col3, col4 = st.columns(4)

col1.metric("📹 Videos", len(df))
col2.metric("⭐ Score medio", round(df["score"].mean(), 2))
col3.metric("📡 Canales", df["canal"].nunique())
col4.metric("📊 Positivos", (df["sentimiento"] == "positivo").sum())

st.markdown("---")

# =========================
# 📊 RANKING
# =========================

st.subheader("📊 Ranking de canales")

ranking = df.groupby("canal")["score"].mean()

st.bar_chart(ranking)

# 🏆 WINNER
st.success(f"🏆 Mejor canal: {ranking.idxmax()}")

# =========================
# 📊 SENTIMIENTO
# =========================

st.subheader("📊 Sentimiento por canal")

sent = df.groupby(["canal", "sentimiento"]).size().unstack(fill_value=0)
st.dataframe(sent)

# =========================
# 📈 EVOLUCIÓN
# =========================

st.subheader("📈 Evolución del score")
st.line_chart(df["score"])

# =========================
# 📊 GLOBAL
# =========================

st.subheader("📊 Sentimiento global")
st.bar_chart(df["sentimiento"].value_counts())