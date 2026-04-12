import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import json
import re
import pandas as pd
import sqlite3
import os

# 🔐 API KEY desde entorno (NO hardcodear)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🧠 init DB
init_db()

st.title("🚀 YouTube AI SaaS Dashboard PRO")

# 🔐 LOGIN SIMPLE
user = st.text_input("Usuario (email o nombre)")

if not user:
    st.stop()

st.success(f"Bienvenido {user} 👋")

# 📺 INPUT CANALES
channels_input = st.text_area("Pega Channel IDs (uno por línea)")

channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

# 🚀 ANALIZAR
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

    st.success("✅ Datos guardados correctamente")

# 📊 LEER DB POR USUARIO (SEGURO)
conn = sqlite3.connect("data.db")
df = pd.read_sql_query(
    "SELECT * FROM videos WHERE user=?",
    conn,
    params=(user,)
)

# 🧪 DEBUG (puedes quitar luego)
# st.write(df)

st.subheader("📋 Histórico del usuario")
st.dataframe(df)

# 📊 DASHBOARD
if not df.empty:

    # 🔢 asegurar tipo numérico
    df["score"] = pd.to_numeric(df["score"], errors="coerce")

    # 📊 COMPARATIVA CANALES
    st.subheader("📊 Comparación de canales")

    canal_score = df.groupby("canal")["score"].mean()
    st.bar_chart(canal_score)

    # 📊 SENTIMIENTO POR CANAL
    st.subheader("📊 Sentimiento por canal")

    tabla = df.groupby(["canal", "sentimiento"]).size().unstack(fill_value=0)
    st.dataframe(tabla)

    # 🏆 GANADOR
    st.subheader("🏆 Canal ganador")

    ganador = canal_score.idxmax()
    st.success(f"🏆 Mejor canal: {ganador}")

    # 📈 EVOLUCIÓN
    st.subheader("📈 Evolución score")
    st.line_chart(df["score"])

    # 📊 GLOBAL
    st.subheader("📊 Sentimiento global")
    st.bar_chart(df["sentimiento"].value_counts())

else:
    st.warning("⚠️ No hay datos todavía. Ejecuta un análisis.")