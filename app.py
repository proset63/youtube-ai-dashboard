import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
import json, re, pandas as pd, sqlite3, os
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
init_db()

st.set_page_config(layout="wide")
st.title("🚀 AI SaaS Dashboard (Multi-Run)")

# 👤 USER
user = st.text_input("Usuario")

if not user:
    st.stop()

# 📥 INPUT
channels_input = st.text_area("Channel IDs")
channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

# 🆕 RUN ID
run_id = datetime.now().strftime("%Y%m%d%H%M%S")

# 🚀 ANALYZE
if st.button("Analizar"):

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

    st.success(f"✅ Run guardado: {run_id}")

# 📦 LOAD DATA
conn = sqlite3.connect("data.db")

df = pd.read_sql_query(
    "SELECT * FROM videos WHERE user=?",
    conn,
    params=(user,)
)

if df.empty:
    st.warning("No hay datos")
    st.stop()

# 🎯 SELECT RUN
runs = df["run_id"].unique()
selected_run = st.selectbox("Selecciona run", runs)

df = df[df["run_id"] == selected_run]

df["score"] = pd.to_numeric(df["score"], errors="coerce")

# 📊 KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Videos", len(df))
col2.metric("Score medio", round(df["score"].mean(), 2))
col3.metric("Canales", df["canal"].nunique())

# 📊 CHARTS
st.subheader("Ranking")
ranking = df.groupby("canal")["score"].mean()
st.bar_chart(ranking)

st.subheader("Sentimiento")
st.bar_chart(df["sentimiento"].value_counts())

st.subheader("Evolución")
st.line_chart(df["score"])