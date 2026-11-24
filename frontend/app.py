import time

import pandas as pd
import streamlit as st

from utils.api import get_cameras, get_roi, login
from utils.auth import do_logout, remember_login, restore_login, wait_for_browser_cookies
from utils.mock_data import init_state
from utils.style import hero, inject_style

st.set_page_config(page_title="AISeeU", page_icon="🚗", layout="wide")
init_state()
inject_style()
restore_login()
wait_for_browser_cookies()

if not st.session_state.auth:
    st.markdown("<style>[data-testid='stSidebarNav'],[data-testid='stSidebar']{display:none}</style>",
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.title("AISeeU")
        st.caption("Multi Zone Vehicle Counting Dashboard")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            ok = st.form_submit_button("Masuk", type="primary", use_container_width=True)
        if ok:
            sukses, hasil = login(u, p)
            if sukses:
                st.session_state.auth, st.session_state.user = True, hasil.get("username", u)
                remember_login()
                time.sleep(0.5)  # beri waktu browser menyimpan cookie
                st.rerun()
            else:
                st.error(hasil)

    st.stop()

with st.sidebar:
    st.caption(f"Masuk sebagai: **{st.session_state.user}**")
    if st.button("Keluar", use_container_width=True):
        do_logout()
        st.rerun()

hero("AISeeU", "Multi Zone Vehicle Counting Dashboard")

cameras = get_cameras()
if not cameras:
    st.warning("Belum ada kamera terdaftar, atau backend tidak bisa dihubungi.")

rois = {c["camera_id"]: get_roi(c["camera_id"]) for c in cameras}
n_zone = sum(len(v) for v in rois.values())
sources = {c.get("current_source") for c in cameras if c.get("current_source")}
if not sources:
    source_label = "-"
elif len(sources) == 1:
    source_label = next(iter(sources))
else:
    source_label = "Campuran"

c1, c2, c3 = st.columns(3)
c1.metric("Kamera terdaftar", len(cameras))
c2.metric("Total zona aktif", n_zone)
c3.metric("Sumber video", source_label)

st.subheader("Status kamera")
if cameras:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Kamera": c["camera_id"],
                    "Sumber": c.get("current_source") or "-",
                    "Zona": len(rois[c["camera_id"]]),
                }
                for c in cameras
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

st.page_link("pages/1_Dashboard.py", label="Buka Dashboard Real Time", icon=":material/monitoring:")
