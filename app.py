import streamlit as st
import os
import sqlite3
import pandas as pd
from datetime import datetime

from googleapiclient.discovery import build
from openai import OpenAI

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# STATE CONTROL (IMPORTANTE)
# =========================
if "run_executed" not in st.session_state:
    st.session_state["run_executed"] = False

if "run_id" not in st.session_state:
    st.session_state["run_id"] = None

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
# SIMPLE LOGIN (opcional)
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

# =========================
# INPUT LIMPIO (CLAVE FIX)
# =========================
st.title("📊 SaaS Dashboard PRO")

input_data = st.text_area(
    "Industries + Channels",
    value="",   # 🔥 IMPORTANTE: vacío
    placeholder="AI:\nOpenAI\nNVIDIA\n\nMarketing:\nNike\nApple"
)

col1, col2 = st.columns(2)

run_btn = col1.button("🚀 Run Analysis")
reset_btn = col2.button("🧹 Reset Run")

# =========================
# RESET LOGIC
# =========================
if reset_btn:
    st.session_state["run_executed"] = False
    st.session_state["run_id"] = None
    st.success("Reset completado")

# =========================
# SOLO EJECUTAR SI HAY INPUT
# =========================
if run_btn and input_data.strip() != "":

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state["run_executed"] = True
    st.session_state["run_id"] = run_id

    st.success(f"Run creado: {run_id}")

# =========================
# SOLO MOSTRAR SI HAY RUN
# =========================
if not st.session_state["run_executed"]:
    st.info("Introduce datos y pulsa Run Analysis")
    st.stop()

# =========================
# LOAD DATA
# =========================
df = pd.read_sql_query("SELECT * FROM analytics", conn)

if df.empty:
    st.warning("No hay datos aún")
    st.stop()

# =========================
# FILTER RUN
# =========================
run_id = st.session_state["run_id"]
df_run = df[df["run_id"] == run_id]

st.subheader("📊 Resultados del Run")

st.dataframe(df_run)

# =========================
# STRIPE STYLE KPIs
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Rows", len(df_run))
col2.metric("Industries", df_run["industry"].nunique() if "industry" in df_run else 0)
col3.metric("Channels", df_run["channel"].nunique() if "channel" in df_run else 0)