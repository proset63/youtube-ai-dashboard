import streamlit as st
import os
import sqlite3
import pandas as pd
from datetime import datetime
import json
import re

from googleapiclient.discovery import build
from openai import OpenAI

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="AI SaaS Stable Dashboard", layout="wide")

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
    video_id TEXT,
    url TEXT,
    engagement REAL,
    business REAL,
    virality REAL,
    social_score REAL,
    social_insight TEXT,
    final_score REAL
)
""")
conn.commit()

# =========================
# LOGIN
# =========================
USERS = {"demo": "1234"}

st.sidebar.title("Login")
user_input = st.sidebar.text_input("User")
pass_input = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if user_input in USERS and USERS[user_input] == pass_input:
        st.session_state["auth"] = True
        st.session_state["user"] = user_input
    else:
        st.sidebar.error("Credenciales incorrectas")

if "auth" not in st.session_state:
    st.stop()

user = st.session_state["user"]

# =========================
# SCORING
# =========================
def engagement_score(text):
    score = 0.5
    if any(x in text.lower() for x in ["how", "tutorial", "best", "guide"]):
        score += 0.2
    return min(score, 1.0)

def business_score(text):
    score = 0.5
    if any(x in text.lower() for x in ["ai", "business", "money", "growth"]):
        score += 0.3
    return min(score, 1.0)

def virality_score(text):
    score = 0.4
    if any(x in text.lower() for x in ["viral", "breaking", "insane"]):
        score += 0.4
    return min(score, 1.0)

# =========================
# COMMENTS YOUTUBE
# =========================
def get_comments(video_id, max_comments=15):
    try:
        req = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_comments,
            textFormat="plainText"
        )
        res = req.execute()

        comments = []
        for item in res.get("items", []):
            comments.append(
                item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            )

        return comments
    except:
        return []

# =========================
# SAFE AI ANALYSIS (FIX JSON ERROR)
# =========================
def analyze_comments(comments):
    if not comments:
        return 0.5, "No comments"

    text = "\n".join(comments[:10])

    prompt = f"""
Devuelve SOLO un JSON válido:

{{
"sentiment": 0-1,
"insight": "1 frase corta"
}}

Comentarios:
{text}
"""

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = res.choices[0].message.content

    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data.get("sentiment", 0.5), data.get("insight", "ok")
    except:
        pass

    return 0.5, "parse error"

# =========================
# UI
# =========================
st.title("📊 Stable AI SaaS Dashboard")

channels = st.text_area("Channels", "Apple\nGoogle\nMeta")

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

            video_id = v["id"]["videoId"]
            title = v["snippet"]["title"]
            url = f"https://www.youtube.com/watch?v={video_id}"

            eng = engagement_score(title)
            biz = business_score(title)
            vir = virality_score(title)

            comments = get_comments(video_id)
            social_score, insight = analyze_comments(comments)

            final = (eng * 0.25 + biz * 0.25 + vir * 0.2 + social_score * 0.3)

            c.execute("""
            INSERT INTO analytics VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                user,
                run_id,
                ch,
                title,
                video_id,
                url,
                eng,
                biz,
                vir,
                social_score,
                insight,
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
# KPIs
# =========================
st.markdown("## 📊 Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("⭐ Score", round(df_run["final_score"].mean(), 2))
c2.metric("📈 Engagement", round(df_run["engagement"].mean(), 2))
c3.metric("💰 Business", round(df_run["business"].mean(), 2))
c4.metric("💬 Social", round(df_run["social_score"].mean(), 2))

st.markdown("---")

# =========================
# GRÁFICOS
# =========================
st.subheader("📊 Channel Performance")
st.bar_chart(df_run.groupby("channel")["final_score"].mean())

st.subheader("💬 Social Sentiment")
st.bar_chart(df_run.groupby("channel")["social_score"].mean())

# =========================
# TABLE
# =========================
st.subheader("📋 Table")
st.dataframe(df_run.sort_values("final_score", ascending=False))

# =========================
# CARDS
# =========================
st.markdown("---")
st.subheader("🎥 Videos + Insights")

for _, row in df_run.iterrows():

    st.markdown(f"""
### 🎬 {row['title']}

⭐ Score: {round(row['final_score'], 2)}  
📈 Engagement: {round(row['engagement'], 2)}  
💰 Business: {round(row['business'], 2)}  
💬 Social: {round(row['social_score'], 2)}  

🧠 Insight: {row['social_insight']}  

👉 [Ver en YouTube]({row['url']})
""")

    st.divider()