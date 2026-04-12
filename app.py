import streamlit as st
import os
import sqlite3
import pandas as pd
import json
import re
from datetime import datetime

from googleapiclient.discovery import build
from openai import OpenAI

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")

# APIs
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# YOUTUBE: SEARCH CHANNEL
# =========================
def search_channel_id(name):
    request = youtube.search().list(
        part="snippet",
        q=name,
        type="channel",
        maxResults=1
    )

    response = request.execute()
    items = response.get("items", [])

    if not items:
        return None

    return items[0]["snippet"]["channelId"]

# =========================
# YOUTUBE: GET VIDEOS
# =========================
def get_videos(channel_id):
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=5,
        order="date"
    )

    response = request.execute()

    videos = []

    for item in response.get("items", []):
        videos.append({
            "title": item["snippet"]["title"],
            "summary": item["snippet"]["description"]
        })

    return videos

# =========================
# OPENAI ANALYSIS
# =========================
def analyze(text):
    prompt = f"""
Devuelve SOLO JSON:
{{
"sentimiento": "positivo|negativo|neutro",
"score": 0.0,
"insight": "1 frase"
}}

Texto:
{text}
"""

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    match = re.search(r"\{.*\}", res.choices[0].message.content, re.DOTALL)

    if match:
        return json.loads(match.group())

    return {"sentimiento": "neutro", "score": 0.5, "insight": "N/A"}

# =========================
# DB
# =========================
conn = sqlite3.connect("data.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    run_id TEXT,
    industry TEXT,
    canal TEXT,
    title TEXT,
    sentiment TEXT,
    score REAL,
    insight TEXT
)
""")

conn.commit()

# =========================
# UI
# =========================
st.title("📊 AI Industry Intelligence SaaS")

user = st.text_input("Usuario")

channels_input = st.text_area("Canales por industria")

run_btn = st.button("🚀 Analizar")

# =========================
# PARSE INDUSTRIES
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

# =========================
# RUN
# =========================
if run_btn:

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    for industry, channels in industries.items():

        for name in channels:

            channel_id = search_channel_id(name)

            if not channel_id:
                st.warning(f"No encontrado: {name}")
                continue

            videos = get_videos(channel_id)

            for v in videos:

                result = analyze(v["title"] + " " + v["summary"])

                c.execute("""
                INSERT INTO videos VALUES (NULL,?,?,?,?,?,?,?,?)
                """, (
                    user,
                    run_id,
                    industry,
                    name,
                    v["title"],
                    result["sentimiento"],
                    float(result["score"]),
                    result["insight"]
                ))

    conn.commit()
    st.success(f"Run completado: {run_id}")

# =========================
# LOAD DATA
# =========================
df = pd.read_sql_query("SELECT * FROM videos", conn)

if df.empty:
    st.stop()

df["score"] = pd.to_numeric(df["score"], errors="coerce")

# =========================
# RUNS
# =========================
runs = df["run_id"].unique()
run = st.selectbox("Selecciona run", runs)

df_run = df[df["run_id"] == run]

# =========================
# DASHBOARD
# =========================
st.subheader("📊 Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Videos", len(df_run))
col2.metric("Score medio", round(df_run["score"].mean(), 2))
col3.metric("Industrias", df_run["industry"].nunique())

st.markdown("---")

# INDUSTRY COMPARISON
st.subheader("🏭 Industry Comparison")
st.bar_chart(df_run.groupby("industry")["score"].mean())

# CHANNEL COMPARISON
st.subheader("📺 Channel Comparison")
st.bar_chart(df_run.groupby("canal")["score"].mean())

# SENTIMENT
st.subheader("💬 Sentiment")
st.bar_chart(df_run["sentiment"].value_counts())

# INSIGHTS
st.subheader("🧠 Insights")
st.dataframe(df_run[["industry","canal","title","insight","score"]])