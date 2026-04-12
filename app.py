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
# DB
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    run_id TEXT,
    industry TEXT,
    channel TEXT,
    title TEXT,
    sentiment TEXT,
    score REAL,
    insight TEXT
)
""")

conn.commit()

# =========================
# AUTH SIMPLE
# =========================
USERS = {
    "demo@saas.com": "1234"
}

st.sidebar.title("🔐 Login")

email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if email in USERS and USERS[email] == password:
        st.session_state["user"] = email
    else:
        st.error("Credenciales incorrectas")

if "user" not in st.session_state:
    st.stop()

user = st.session_state["user"]

# =========================
# YOUTUBE FUNCTIONS (REAL API)
# =========================
def search_channel(name):
    res = youtube.search().list(
        part="snippet",
        q=name,
        type="channel",
        maxResults=1
    ).execute()

    items = res.get("items", [])
    if not items:
        return None

    return items[0]["snippet"]["channelId"]


def get_videos(channel_id):
    res = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=5,
        order="date"
    ).execute()

    videos = []

    for item in res.get("items", []):
        videos.append({
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"]
        })

    return videos

# =========================
# OPENAI ANALYSIS
# =========================
def analyze_text(text):
    prompt = f"""
Devuelve SOLO JSON:

{{
"sentiment": "positive|neutral|negative",
"score": 0-1,
"insight": "1 frase clara"
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

    return {"sentiment": "neutral", "score": 0.5, "insight": "N/A"}

# =========================
# UI
# =========================
st.title("📊 SaaS Intelligence Dashboard PRO")

input_data = st.text_area(
    "Industries + Channels",
    placeholder="""
AI:
OpenAI
Google Developers
NVIDIA

Marketing:
HubSpot
Nike
Apple
"""
)

run_btn = st.button("🚀 Run Analysis")

# =========================
# PARSE INPUT
# =========================
industries = {}
current = None

for line in input_data.split("\n"):
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
# RUN PIPELINE (REAL YOUTUBE + AI)
# =========================
if run_btn:

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    for industry, channels in industries.items():

        for channel_name in channels:

            channel_id = search_channel(channel_name)

            if not channel_id:
                st.warning(f"No encontrado: {channel_name}")
                continue

            videos = get_videos(channel_id)

            for v in videos:

                text = v["title"] + " " + v["description"]

                result = analyze_text(text)

                c.execute("""
                INSERT INTO analytics VALUES (NULL,?,?,?,?,?,?,?,?)
                """, (
                    user,
                    run_id,
                    industry,
                    channel_name,
                    v["title"],
                    result["sentiment"],
                    float(result["score"]),
                    result["insight"]
                ))

    conn.commit()

    st.success(f"Run completado: {run_id}")

# =========================
# LOAD DATA
# =========================
df = pd.read_sql_query(
    f"SELECT * FROM analytics WHERE user='{user}'",
    conn
)

if df.empty:
    st.warning("No data yet")
    st.stop()

# =========================
# RUN SELECTOR
# =========================
runs = df["run_id"].unique()
run = st.selectbox("Select Run", runs)

df_run = df[df["run_id"] == run]

# =========================
# STRIPE STYLE KPI
# =========================
st.subheader("📊 Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Videos", len(df_run))
col2.metric("Avg Score", round(df_run["score"].mean(), 2))
col3.metric("Industries", df_run["industry"].nunique())
col4.metric("Channels", df_run["channel"].nunique())

st.markdown("---")

# =========================
# INDUSTRY COMPARISON
# =========================
st.subheader("🏭 Industry Performance")
st.bar_chart(df_run.groupby("industry")["score"].mean())

# =========================
# CHANNEL COMPARISON
# =========================
st.subheader("📺 Channel Performance")
st.bar_chart(df_run.groupby("channel")["score"].mean())

# =========================
# SENTIMENT
# =========================
st.subheader("💬 Sentiment Breakdown")
st.bar_chart(df_run["sentiment"].value_counts())

# =========================
# TABLE
# =========================
st.subheader("📋 Insights")
st.dataframe(df_run[[
    "industry",
    "channel",
    "title",
    "sentiment",
    "score",
    "insight"
]])