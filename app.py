import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import json
import re
import pandas as pd
import sqlite3
import os

# 🔐 OpenAI key desde Streamlit Secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

init_db()

st.title("🚀 YouTube AI SaaS Dashboard PRO")

# 👤 Usuario
user = st.text_input("Usuario")

if not user:
    st.stop()

st.success(f"Bienvenido {user} 👋")

# 📺 Canales input
channels_input = st.text_area("Pega Channel IDs (uno por línea)")

channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

# 📊 ANALIZAR
if st.button("Analizar"):

    for channel_id in channels:

        videos = get_videos(channel_id)

        for v in videos:

            prompt = f"""
Devuelve SOLO JSON válido:

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

    st.success("✅ Datos guardados")

# 📦 CARGAR DATA
conn = sqlite3.connect("data.db")
df = pd.read_sql_query(
    "SELECT * FROM videos WHERE user=?",
    conn,
    params=(user,)
)

st.subheader("📋 Datos del usuario")
st.dataframe(df)

# 🚨 SI NO HAY DATOS
if df.empty:
    st.warning("⚠️ No hay datos aún. Ejecuta análisis.")
    st.stop()

# 🔧 DEBUG
st.subheader("🔍 Debug canales")
st.write(df["canal"].value_counts())

# 📌 LISTA FIJA DE CANALES (IMPORTANTE)
expected_channels = channels

# 🔢 asegurar tipo
df["score"] = pd.to_numeric(df["score"], errors="coerce")

# 📊 RANKING CANALES
st.subheader("📊 Ranking de canales")

ranking = df.groupby("canal")["score"].mean()

# 👉 fuerza aparición de TODOS los canales
ranking = ranking.reindex(expected_channels, fill_value=0)

st.bar_chart(ranking)

# 🏆 GANADOR
winner = ranking.idxmax()
st.success(f"🏆 Mejor canal: {winner}")

# 📊 SENTIMIENTO POR CANAL
st.subheader("📊 Sentimiento por canal")

tabla = df.groupby(["canal", "sentimiento"]).size().unstack(fill_value=0)

# 👉 asegura columnas completas
tabla = tabla.reindex(expected_channels, fill_value=0)

st.dataframe(tabla)

# 📈 EVOLUCIÓN GLOBAL
st.subheader("📈 Evolución del score")
st.line_chart(df["score"])

# 📊 GLOBAL SENTIMENT
st.subheader("📊 Sentimiento global")
st.bar_chart(df["sentimiento"].value_counts())