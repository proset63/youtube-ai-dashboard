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

st.set_page_config(page_title="Analytics", layout="wide")

# =========================
# STYLE (STRIPE LIKE)
# =========================
st.markdown("""
    <style>
        .main { background-color: #ffffff; }
        h1, h2, h3 { font-weight: 600; color: #111827; }
        .stMetric { background-color: #f9fafb; padding: 15px; border-radius: 12px; }
        .block-container { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("📊 Analytics")

    user = st.text_input("Usuario")

    st.markdown("---")

    channels_input = st.text_area("Channel IDs")

    run_btn = st.button("Run analysis")

    st.caption("Cada run es un snapshot")

# =========================
# MAIN
# =========================
st.title("📈 Dashboard")

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

    st.success("Run completed")

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
    st.info("No data yet")
    st.stop()

df["score"] = pd.to_numeric(df["score"], errors="coerce")

# =========================
# RUNS
# =========================
runs = sorted(df["run_id"].unique(), reverse=True)

col1, col2 = st.columns([1,1])

with col1:
    run_1 = st.selectbox("Current run", runs)

with col2:
    run_2 = st.selectbox("Previous run", runs)

df1 = df[df["run_id"] == run_1]
df2 = df[df["run_id"] == run_2]

# =========================
# KPI STRIPE STYLE
# =========================
st.markdown("### Overview")

k1, k2, k3, k4 = st.columns(4)

k1.metric("Videos", len(df1))
k2.metric("Avg Score", round(df1["score"].mean(), 2))
k3.metric("Channels", df1["canal"].nunique())
k4.metric("Run", run_1)

st.markdown("---")

# =========================
# COMPARISON
# =========================
st.markdown("### Performance change")

score1 = df1["score"].mean()
score2 = df2["score"].mean()
delta = score1 - score2

c1, c2, c3 = st.columns(3)

c1.metric("Current", round(score1, 2))
c2.metric("Previous", round(score2, 2))
c3.metric("Change", round(delta, 2))

st.markdown("---")

# =========================
# CHANNEL PERFORMANCE
# =========================
st.markdown("### Channel performance")

r1 = df1.groupby("canal")["score"].mean()
r2 = df2.groupby("canal")["score"].mean()

compare = pd.DataFrame({
    "current": r1,
    "previous": r2
}).fillna(0)

compare["delta"] = compare["current"] - compare["previous"]

st.bar_chart(compare["delta"])

st.markdown("---")

# =========================
# SENTIMENT
# =========================
st.markdown("### Sentiment")

st.bar_chart(df1["sentimiento"].value_counts())