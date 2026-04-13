import streamlit as st
import os
import sqlite3
import pandas as pd
from datetime import datetime

from googleapiclient.discovery import build

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

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
    engagement REAL,
    business REAL,
    virality REAL,
    final_score REAL
)
""")
conn.commit()

# =========================
# LOGIN SIMPLE
# =========================
USERS = {"demo": "1234"}

st.sidebar.title("Login")
user = st.sidebar.text_input("User")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if user in USERS and USERS[user] == password:
        st.session_state["auth"] = True
        st.session_state["user"] = user
    else:
        st.error("Credenciales incorrectas")

if "auth" not in st.session_state:
    st.stop()

user = st.session_state["user"]
st.sidebar.success(user)

# =========================
# SCORING
# =========================
def engagement_score(text):
    score = 0.5
    if any(x in text.lower() for x in ["how", "tutorial", "best", "guide"]):
        score += 0.2
    if len(text) > 60:
        score += 0.1
    if "!" in text:
        score += 0.2
    return min(score, 1.0)

def business_score(text):
    score = 0.5
    if any(x in text.lower() for x in ["ai", "business", "money", "growth"]):
        score += 0.3
    if any(x in text.lower() for x in ["review", "vs"]):
        score += 0.2
    return min(score, 1.0)

def virality_score(text):
    score = 0.4
    if any(x in text.lower() for x in ["breaking", "viral", "insane"]):
        score += 0.4
    if "!" in text:
        score += 0.1
    return min(score, 1.0)

# =========================
# UI
# =========================
st.title("📊 AI SaaS Dashboard (Stripe Style)")

channels = st.text_area("Channels (uno por línea)", "Apple\nGoogle\nMeta")

col1, col2 = st.columns(2)
run_btn = col1.button("🚀 Run")
reset_btn = col2.button("🧹 Reset")

# =========================
# RESET
# =========================
if reset_btn:
    c.execute("DELETE FROM analytics WHERE user=?", (user,))
    conn.commit()
    st.success("Reset OK")
    st.rerun()

# =========================
# RUN PIPELINE
# =========================
if run_btn:

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    for ch in channels.split("\n"):

        ch = ch.strip()
        if not ch:
            continue

        res = youtube.search().list(
            part="snippet",
            q=ch,
            type="channel",
            maxResults=1
        ).execute()

        items = res.get("items", [])
        if not items:
            continue

        channel_id = items[0]["snippet"]["channelId"]

        videos = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            maxResults=5,
            order="date"
        ).execute()

        for v in videos.get("items", []):

            title = v["snippet"]["title"]
            desc = v["snippet"]["description"]

            text = title + " " + desc

            eng = engagement_score(text)
            biz = business_score(text)
            vir = virality_score(text)

            final = (eng * 0.4 + biz * 0.3 + vir * 0.3)

            c.execute("""
            INSERT INTO analytics VALUES (NULL,?,?,?,?,?,?,?,?)
            """, (
                user,
                run_id,
                ch,
                title,
                eng,
                biz,
                vir,
                final
            ))

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
    st.warning("No data yet")
    st.stop()

# =========================
# RUN SELECTOR
# =========================
runs = sorted(df["run_id"].unique(), reverse=True)
selected_run = st.selectbox("Run", runs)

df_run = df[df["run_id"] == selected_run]

# =========================
# KPIs (STRIPE STYLE)
# =========================
st.markdown("## 📊 Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("⭐ Score", round(df_run["final_score"].mean(), 2))
c2.metric("📈 Engagement", round(df_run["engagement"].mean(), 2))
c3.metric("💰 Business", round(df_run["business"].mean(), 2))
c4.metric("🔥 Virality", round(df_run["virality"].mean(), 2))

st.markdown("---")

# =========================
# CHARTS
# =========================
st.subheader("Channel Performance")
st.bar_chart(df_run.groupby("channel")["final_score"].mean())

# =========================
# TABLE
# =========================
st.subheader("Table")
st.dataframe(df_run.sort_values("final_score", ascending=False))

# =========================
# CARDS VIEW
# =========================
st.markdown("---")
st.subheader("🎥 Cards View")

for ch in df_run["channel"].unique():

    st.markdown(f"## {ch}")

    sub = df_run[df_run["channel"] == ch]

    for _, row in sub.iterrows():

        st.markdown(f"""
### 🎬 {row['title']}

⭐ {round(row['final_score'], 2)}  
📈 {round(row['engagement'], 2)}  
💰 {round(row['business'], 2)}  
🔥 {round(row['virality'], 2)}
""")

        st.divider()