import streamlit as st
import os
import pandas as pd
import sqlite3
from datetime import datetime

# OpenAI
from openai import OpenAI

# YouTube API (Google Cloud)
from googleapiclient.discovery import build

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# =========================
# YOUTUBE SEARCH CHANNEL
# =========================
def search_channel(name):
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
# UI
# =========================
st.title("📊 AI SaaS Dashboard")

user = st.text_input("Usuario")

channels = st.text_area("Canales (uno por línea)")

run = st.button("Analizar")

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
    canal TEXT
)
""")

conn.commit()

# =========================
# RUN
# =========================
if run:

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    for name in channels.split("\n"):

        name = name.strip()

        if not name:
            continue

        channel_id = search_channel(name)

        if channel_id:
            c.execute("""
            INSERT INTO videos VALUES (NULL,?,?,?)
            """, (user, run_id, channel_id))

            st.success(f"{name} → {channel_id}")
        else:
            st.warning(f"No encontrado: {name}")

    conn.commit()

    st.success("Run completado")

# =========================
# VIEW DATA
# =========================
df = pd.read_sql_query("SELECT * FROM videos", conn)

st.dataframe(df)