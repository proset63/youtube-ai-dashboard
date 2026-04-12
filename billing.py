import streamlit as st

PLANS = {
    "free": {"runs": 2},
    "pro": {"runs": 50},
    "business": {"runs": 999}
}

def get_plan(user):
    if user == "admin@saas.com":
        return "business"
    return "free"