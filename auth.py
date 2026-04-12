import streamlit as st

USERS = {
    "demo@saas.com": "1234",
    "admin@saas.com": "admin"
}

def login():
    st.sidebar.title("🔐 Login")

    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        if email in USERS and USERS[email] == password:
            st.session_state["user"] = email
            st.success("Login correcto")
        else:
            st.error("Credenciales incorrectas")

def get_user():
    return st.session_state.get("user", None)