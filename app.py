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
st.set_page_config(page_title="Stripe-like AI SaaS", layout="wide")

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
    channel TEXT,
    title TEXT,
    sentiment REAL,
    engagement REAL,
    business REAL,
    virality REAL,
    final_score REAL
)
""")

conn.commit()

# =========================
# LOGIN
# =========================
USERS = {"demo@saas.com": "1234"}

def login():
    st.title("🔐 SaaS Login")

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
# STATE
# =========================
if "run_id" not in st.session_state:
    st.session_state["run_id"] = None

# =========================
# SCORING FUNCTIONS
# =========================
def engagement_score(text):
    score = 0.5
    if any(x in text.lower() for x in ["how", "tutorial", "guide", "best"]):
        score += 0.2
    if len(text) > 60:
        score += 0.1
    if any(x in text.lower() for x in ["!", "now", "new"]):
        score += 0.2
    return min(score, 1.0)


def business_score(text):
    score = 0.5
    if any(x in text.lower() for x in ["ai", "business", "money", "growth"]):
        score += 0.3
    if any(x in text.lower() for x in ["review", "vs", "best"]):
        score += 0.2
    return min(score, 1.0)


def virality_score(text):
    score = 0.4
    if any(x in text.lower() for x in ["breaking", "shocking", "insane", "viral"]):
        score += 0.4
    if "!" in text:
        score += 0.1
    if text.isupper():
        score += 0.1
    return min(score, 1.0)

# =========================
# UI
# =========================
st.title("📊 Stripe-like AI SaaS Dashboard")

input_data = st.text_area(
    "Channels (uno por línea)",
    value="",
    placeholder="Apple\nGoogle\nMeta"
)

col1, col2 = st.columns(2)
run_btn = col1.button("🚀 Run Analysis")
reset_btn = col2.button("🧹 Reset")

# =========================
# RESET
# =========================
if reset_btn:
    c.execute("DELETE FROM analytics WHERE user=?", (user,))
    conn.commit()
    st.session_state["run_id"] = None
    st.success("Datos eliminados")
    st.rerun()

# =========================
# RUN PIPELINE
# =========================
if run_btn and input_data.strip() != "":

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state["run_id"] = run_id

    st.success(f"RUN: {run_id}")

    for channel_name in input_data.split("\n"):

        channel_name = channel_name.strip()
        if not channel_name:
            continue

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
                order="date",
                type="video"
            ).execute()

            for v in videos.get("items", []):

                title = v["snippet"]["title"]
                desc = v["snippet"]["description"]

                text = title + " " + desc

                # SCORES
                sent = 0.5
                eng = engagement_score(text)
                biz = business_score(text)
                vir = virality_score(text)

                final = (sent * 0.4 + eng * 0.2 + biz * 0.2 + vir * 0.2)

                # SAVE
                c.execute("""
                INSERT INTO analytics VALUES (NULL,?,?,?,?,?,?,?,?,?)
                """, (
                    user,
                    run_id,
                    channel_name,
                    title,
                    sent,
                    eng,
                    biz,
                    vir,
                    final
                ))

        except Exception as e:
            st.error(f"Error: {e}")

    conn.commit()
    st.rerun()

# =========================
# LOAD DATA
# =========================
df = pd.read_sql_query(
    "SELECT * FROM analytics WHERE user=?",
    conn,
    params=(user,)
)

if df.empty:
    st.info("No hay datos aún")
    st.stop()

# =========================
# RUN SELECTOR
# =========================
runs = sorted(df["run_id"].unique(), reverse=True)

selected_run = st.selectbox("Selecciona run", runs)

df_run = df[df["run_id"] == selected_run]

# =========================
# STRIPE STYLE KPIs
# =========================
st.markdown("## 📊 Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("⭐ Final Score", round(df_run["final_score"].mean(), 2))
col2.metric("📈 Engagement", round(df_run["engagement"].mean(), 2))
col3.metric("💰 Business", round(df_run["business"].mean(), 2))
col4.metric("🔥 Virality", round(df_run["virality"].mean(), 2))

st.markdown("---")

# =========================
# CHARTS
# =========================
st.subheader("📊 Channel Performance")

st.bar_chart(df_run.groupby("channel")["final_score"].mean())

st.subheader("💰 Business Value")

st.bar_chart(df_run.groupby("channel")["business"].mean())

st.subheader("🔥 Virality")

st.bar_chart(df_run.groupby("channel")["virality"].mean())

# =========================
# TABLE
# =========================
st.subheader("📋 Insights Ranking")

st.dataframe(
    df_run.sort_values("final_score", ascending=False)[[
        "channel",
        "title",
        "final_score",
        "engagement",
        "business",
        "virality"
    ]]
)