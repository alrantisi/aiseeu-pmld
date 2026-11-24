import streamlit as st

CSS = """
<style>
html {font-size: clamp(16px, 0.9vw, 30px) !important;}
.block-container {max-width: 100% !important; padding: 4rem 1.6rem 2rem 1.6rem !important;}
section[data-testid="stSidebar"] {width: 12rem !important; min-width: 12rem !important;}
h1 {font-weight: 700; letter-spacing: -0.3px;}
[data-testid="stMetric"] {background:#131c24; border:1px solid #243240; border-radius:6px; padding:12px 14px;}
[data-testid="stMetricValue"] {font-size: 1.9rem; font-weight: 600;}
[data-testid="stMetricLabel"] p {font-size: .9rem; color: #9fb0bf;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 6px;}
.stButton>button, .stFormSubmitButton>button {border-radius: 6px;}
.ptitle {display:flex; align-items:baseline; gap:14px; border-bottom:1px solid #243240; padding-bottom:10px; margin-bottom:18px;}
.ptitle h1 {margin:0; padding:0; font-size:1.7rem;}
.ptitle span {color:#9fb0bf; font-size:.95rem;}
</style>
"""


def inject_style():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle=""):
    st.markdown(
        f'<div class="ptitle"><h1>{title}</h1><span>{subtitle}</span></div>',
        unsafe_allow_html=True,
    )
