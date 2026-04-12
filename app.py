import streamlit as st
from openai import OpenAI
from youtube_rss import get_videos
from db import init_db, save_video
from auth import login, get_user
from billing import get_plan
import sqlite3
import pandas as pd
import json, re
from datetime import datetime

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

init_db()

st.set_page_config(page_title="AI SaaS", layout="wide")

# 🔐 LOGIN
login()
user = get_user()

if not user:
    st.stop()

plan = get_plan(user)

st.sidebar.success(f"Plan: {plan}")

# 📥 INPUT
st.title("📊 AI Brand Intelligence SaaS")

channels_input = st.text_area("Channel IDs")
channels = [c.strip() for c in channels_input.split("\n") if c.strip()]

run_btn = st.button("🚀 Run analysis")

run_id = datetime.now().strftime("%Y%m%d%H%M%S")

# 🚀 RUN
if run_btn:

    for ch in channels:

        videos = get_videos(ch)

        for v in videos:

            prompt = f"""
Devuelve JSON:
{{
"sentimiento": "positivo|negativo|neutro",
"score": 0.0,
"resumen": "1 frase"
}}

Texto:
{v['title']} - {v['summary']}
"""

            res = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            text = res.choices[0].message.content
            match = re.search(r"\{.*\}", text, re.DOTALL)

            if match:
                data = json.loads(match.group())

                save_video(
                    user,
                    run_id,
                    ch,
                    v["title"],
                    data["sentimiento"],
                    float(data["score"]),
                    data["resumen"]
                )

    st.success("Run completado")

# 📦 LOAD DATA
conn = sqlite3.connect("data.db")

df = pd.read_sql_query(
    "SELECT * FROM videos WHERE user=?",
    conn,
    params=(user,)
)

if df.empty:
    st.stop()

df["score"] = pd.to_numeric(df["score"])

# 📊 RUNS
runs = df["run_id"].unique()

run = st.selectbox("Run", runs)

df = df[df["run_id"] == run]

# 📊 KPIs
col1, col2, col3 = st.columns(3)

col1.metric("Videos", len(df))
col2.metric("Score", round(df["score"].mean(), 2))
col3.metric("Canales", df["canal"].nunique())

# 📊 CHART
st.bar_chart(df.groupby("canal")["score"].mean())
st.bar_chart(df["sentimiento"].value_counts())