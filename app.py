import streamlit as st
import os
import sqlite3
import pandas as pd
from datetime import datetime
from googleapiclient.discovery import build

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

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
    title TEXT
)
""")
conn.commit()

# =========================
# LOGIN SIMPLE
# =========================
USERS = {"demo@saas.com": "1234"}

st.sidebar.title("Login")
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if email in USERS and USERS[email] == password:
        st.session_state["auth"] = True
        st.session_state["user"] = email

if "auth" not in st.session_state:
    st.stop()

user = st.session_state["user"]
st.sidebar.success(user)

# =========================
# STATE
# =========================
if "run_id" not in st.session_state:
    st.session_state["run_id"] = None

# =========================
# UI
# =========================
st.title("📊 YouTube SaaS DEBUG")

input_data = st.text_area(
    "Canales (uno por línea)",
    placeholder="Apple\nGoogle\nMeta"
)

col1, col2 = st.columns(2)
run_btn = col1.button("🚀 Run")
reset_btn = col2.button("🧹 Reset")

# =========================
# RESET REAL
# =========================
if reset_btn:
    c.execute("DELETE FROM analytics WHERE user=?", (user,))
    conn.commit()
    st.session_state["run_id"] = None
    st.success("Datos borrados")
    st.rerun()

# =========================
# RUN PIPELINE (SEGURO)
# =========================
if run_btn and input_data.strip() != "":

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state["run_id"] = run_id

    st.success(f"RUN: {run_id}")

    for channel_name in input_data.split("\n"):

        channel_name = channel_name.strip()

        if not channel_name:
            continue

        st.write("🔍 Buscando:", channel_name)

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
                st.warning("No encontrado")
                continue

            channel_id = items[0]["snippet"]["channelId"]

            # GET VIDEOS
            videos = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=3,
                order="date",
                type="video"
            ).execute()

            for v in videos.get("items", []):

                title = v["snippet"]["title"]

                st.write("💾 Guardando:", title)

                c.execute("""
                INSERT INTO analytics VALUES (NULL,?,?,?,?)
                """, (
                    user,
                    run_id,
                    channel_name,
                    title
                ))

        except Exception as e:
            st.error(f"Error: {e}")

    conn.commit()
    st.success("Datos guardados")
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
    st.warning("No hay datos aún")
    st.stop()

# =========================
# RUN SELECTOR
# =========================
runs = sorted(df["run_id"].unique(), reverse=True)

selected_run = st.selectbox("Selecciona run", runs)

df_run = df[df["run_id"] == selected_run]

# =========================
# KPIs
# =========================
st.subheader("📊 KPIs")

col1, col2 = st.columns(2)

col1.metric("Videos", len(df_run))
col2.metric("Canales", df_run["channel"].nunique())

# =========================
# CHART
# =========================
st.subheader("📺 Videos por canal")

st.bar_chart(df_run["channel"].value_counts())

# =========================
# TABLE
# =========================
st.subheader("📋 Datos")

st.dataframe(df_run)