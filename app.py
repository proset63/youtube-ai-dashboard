import streamlit as st
import os
import pandas as pd
import sqlite3
from datetime import datetime

from googleapiclient.discovery import build

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# =========================
# YOUTUBE SEARCH
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
# DB
# =========================
conn = sqlite3.connect("data.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    run_id TEXT,
    canal TEXT,
    title TEXT
)
""")

conn.commit()

# =========================
# UI
# =========================
st.title("📊 AI SaaS Dashboard PRO")

user = st.text_input("Usuario")

channels_input = st.text_area("Canales (uno por línea)")

run_btn = st.button("🚀 Analizar")

# =========================
# RUN
# =========================
if run_btn:

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    for name in channels_input.split("\n"):
        name = name.strip()

        if not name:
            continue

        channel_id = search_channel(name)

        if channel_id:
            c.execute("""
            INSERT INTO videos VALUES (NULL,?,?,?,?)
            """, (user, run_id, channel_id, f"Video de {name}"))

            st.success(f"{name} → {channel_id}")
        else:
            st.warning(f"No encontrado: {name}")

    conn.commit()

    st.success(f"Run creado: {run_id}")

# =========================
# LOAD DATA
# =========================
df = pd.read_sql_query("SELECT * FROM videos", conn)

st.markdown("---")
st.subheader("📦 Dataset")

st.dataframe(df)

if df.empty:
    st.stop()

# =========================
# RUN SELECTOR
# =========================
runs = df["run_id"].unique()
run = st.selectbox("Selecciona run", runs)

df_run = df[df["run_id"] == run]

# =========================
# KPI
# =========================
st.subheader("📊 KPIs")

col1, col2, col3 = st.columns(3)

col1.metric("Videos", len(df_run))
col2.metric("Canales", df_run["canal"].nunique())
col3.metric("Runs totales", len(runs))

# =========================
# COMPARATIVAS CANALES
# =========================
st.subheader("📺 Comparativa por canal")

channel_counts = df_run["canal"].value_counts()
st.bar_chart(channel_counts)

# =========================
# TABLA
# =========================
st.subheader("📋 Detalle")

st.dataframe(df_run)

# =========================
# DEBUG (IMPORTANTE)
# =========================
with st.expander("🔍 Debug"):
    st.write("Columnas:", df_run.columns)
    st.write(df_run)