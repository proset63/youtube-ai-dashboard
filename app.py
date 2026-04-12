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
# SIDEBAR
# =========================
with st.sidebar:
    st.title("📊 AI SaaS")

    user = st.text_input("Usuario").strip().lower()

    st.markdown("### 🏭 Input por industria")
    channels_input = st.text_area(
        "Formato:\nMARKETING:\nchannel1\nchannel2\n\nAI:\nchannel3"
    )

    run_btn = st.button("🚀 Analizar")

# =========================
# MAIN
# =========================
st.title("📈 Industry Intelligence SaaS")

if not user:
    st.stop()

# =========================
# PARSE INDUSTRIES (CLAVE)
# =========================
industries = {}
current = None

for line in channels_input.split("\n"):
    line = line.strip()

    if not line:
        continue

    if line.endswith(":"):
        current = line.replace(":", "")
        industries[current] = []
    else:
        if current:
            industries[current].append(line)

run_id = datetime.now().strftime("%Y%m%d%H%M%S")

# =========================
# RUN ANALYSIS
# =========================
if run_btn:

    for industry, channels in industries.items():

        for channel_id in channels:

            videos = get_videos(channel_id)

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
                        industry,
                        channel_id,
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
# RUNS FIX
# =========================
runs = sorted(df["run_id"].dropna().unique(), reverse=True)

if len(runs) == 0:
    st.stop()

run_1 = runs[0]
run_2 = runs[1] if len(runs) > 1 else runs[0]

df1 = df[df["run_id"] == run_1]
df2 = df[df["run_id"] == run_2]

# =========================
# STRIPE OVERVIEW
# =========================
st.markdown("### 📊 Overview")

score_now = df1["score"].mean()
score_prev = df2["score"].mean()

delta = score_now - score_prev

col1, col2, col3 = st.columns(3)

col1.metric("Videos", len(df1), len(df1)-len(df2))
col2.metric("Score", round(score_now,2), f"{delta:+.2f}")
col3.metric("Industries", df1["industry"].nunique())

# =========================
# INDUSTRY COMPARISON (CLAVE)
# =========================
st.markdown("---")
st.subheader("🏭 Industry Comparison")

industry_scores = df1.groupby("industry")["score"].mean()

st.bar_chart(industry_scores)

best_industry = industry_scores.idxmax()
st.success(f"🏆 Best performing industry: {best_industry}")

# =========================
# CHANNEL PERFORMANCE
# =========================
st.subheader("📊 Channel Performance")

channel_scores = df1.groupby("canal")["score"].mean()

st.bar_chart(channel_scores)

# =========================
# SENTIMENT
# =========================
st.subheader("📊 Sentiment")

st.bar_chart(df1["sentimiento"].value_counts())

# =========================
# TREND
# =========================
st.subheader("📈 Trend")

st.line_chart(df1["score"])