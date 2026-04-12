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
st.set_page_config(page_title="AI SaaS PRO", layout="wide")

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
# LOGIN
# =========================
USERS = {
    "demo@saas.com": "1234",
    "admin@saas.com": "admin"
}

def login():
    st.title("🔐 Login SaaS")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email in USERS and USERS[email] == password:
            st.session_state["auth"] = True
            st.session_state["user"] = email
        else:
            st.error("Credenciales incorrectas")

if "auth" not in st.session_state:
    login()
    st.stop()

user = st.session_state["user"]
st.sidebar.success(f"👤 {user}")

# =========================
# STATE CONTROL
# =========================
if "run_id" not in st.session_state:
    st.session_state["run_id"] = None

# =========================
# UI INPUT
# =========================
st.title("📊 SaaS Intelligence PRO")

input_data = st.text_area(
    "Industries + Channels",
    value="",
    placeholder="AI:\nOpenAI\nNVIDIA\n\nMarketing:\nNike\nApple"
)

col1, col2 = st.columns(2)
run_btn = col1.button("🚀 Run Analysis")
reset_btn = col2.button("🧹 Reset")

# =========================
# RESET
# =========================
if reset_btn:
    st.session_state["run_id"] = None
    st.success("Reset hecho")
    st.stop()

# =========================
# RUN PIPELINE
# =========================
if run_btn and input_data.strip() != "":

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state["run_id"] = run_id

    st.success(f"Run creado: {run_id}")

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
    # YOUTUBE + AI
    # =========================
    for industry, channels in industries.items():

        for channel_name in channels:

            try:
                # SEARCH CHANNEL
                res = youtube.search().list(
                    part="snippet",
                    q=channel_name,
                    type="channel",
                    maxResults=1
                ).execute()

                items = res.get("items", [])
                if not items:
                    continue

                channel_id = items[0]["snippet"]["channelId"]

                # GET VIDEOS
                videos = youtube.search().list(
                    part="snippet",
                    channelId=channel_id,
                    maxResults=5,
                    order="date"
                ).execute()

                for v in videos.get("items", []):

                    title = v["snippet"]["title"]
                    desc = v["snippet"]["description"]

                    text = title + " " + desc

                    # IA ANALYSIS
                    ai = client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[{
                            "role": "user",
                            "content": f"""
Devuelve JSON:
{{
"sentiment": "positive|neutral|negative",
"score": 0-1,
"insight": "1 frase"
}}

Texto:
{text}
"""
                        }]
                    )

                    match = re.search(r"\{.*\}", ai.choices[0].message.content, re.DOTALL)

                    if match:
                        data = json.loads(match.group())
                    else:
                        data = {"sentiment": "neutral", "score": 0.5, "insight": "N/A"}

                    # SAVE
                    c.execute("""
                    INSERT INTO analytics VALUES (NULL,?,?,?,?,?,?,?,?)
                    """, (
                        user,
                        run_id,
                        industry,
                        channel_name,
                        title,
                        data["sentiment"],
                        float(data["score"]),
                        data["insight"]
                    ))

            except Exception as e:
                st.error(f"Error en {channel_name}: {e}")

    conn.commit()

# =========================
# LOAD DATA
# =========================
df = pd.read_sql_query(
    f"SELECT * FROM analytics WHERE user='{user}'",
    conn
)

if df.empty:
    st.info("No hay datos aún")
    st.stop()

# =========================
# SELECT RUN
# =========================
runs = df["run_id"].unique()
run = st.selectbox("Selecciona run", runs)

df_run = df[df["run_id"] == run]

# =========================
# KPI STRIPE STYLE
# =========================
st.subheader("📊 Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Videos", len(df_run))
col2.metric("Avg Score", round(df_run["score"].mean(), 2))
col3.metric("Industries", df_run["industry"].nunique())
col4.metric("Channels", df_run["channel"].nunique())

st.markdown("---")

# =========================
# CHARTS
# =========================
st.subheader("🏭 Industry Comparison")
st.bar_chart(df_run.groupby("industry")["score"].mean())

st.subheader("📺 Channel Comparison")
st.bar_chart(df_run.groupby("channel")["score"].mean())

st.subheader("💬 Sentiment")
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