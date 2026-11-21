import time

import streamlit as st
from streamlit_cookies_controller import CookieController

from utils.api import get_session_token, logout, restore_session
from utils.mock_data import init_state

COOKIE_NAME = "pmld_session"
COOKIE_MAX_AGE = 24 * 60 * 60  # login diingat 1 hari


def remember_login():
    """Simpan tiket login dari backend ke cookie browser (setelah login sukses)."""
    token = get_session_token()
    if token:
        CookieController().set(COOKIE_NAME, token, max_age=COOKIE_MAX_AGE)


def forget_login():
    """Hapus cookie login dari browser."""
    try:
        CookieController().remove(COOKIE_NAME)
    except KeyError:
        pass


def restore_login():
    """Kalau sesi Streamlit baru (misal setelah refresh) tapi cookie login masih
    ada di browser, pulihkan login tanpa form."""
    ss = st.session_state
    if ss.auth:
        return
    token = CookieController().get(COOKIE_NAME)
    if not token or ss.get("_restore_token") == token:
        return
    ss["_restore_token"] = token
    status, user = restore_session(token)
    if status == "ok":
        ss.auth = True
        ss.user = user.get("username", "")
    elif status == "invalid":
        forget_login()


def wait_for_browser_cookies():
    """Tunggu sebentar (sekali per sesi) supaya cookie browser sempat terbaca,
    jadi form login tidak berkedip saat halaman di-refresh."""
    ss = st.session_state
    if ss.auth or ss.get("_cookie_wait_done"):
        return
    ss["_cookie_wait_done"] = True
    st.markdown("<style>[data-testid='stSidebarNav'],[data-testid='stSidebar']{display:none}</style>",
                unsafe_allow_html=True)
    st.caption("Memeriksa sesi login...")
    time.sleep(0.6)
    st.rerun()


def do_logout():
    """Logout di backend, hapus cookie browser, dan kosongkan status login."""
    forget_login()
    logout()
    st.session_state.auth = False
    st.session_state.user = ""
    time.sleep(0.5)  # beri waktu browser menjalankan penghapusan cookie


def require_login():
    """Dipanggil di awal setiap halaman: blok akses jika belum login."""
    init_state()
    restore_login()
    wait_for_browser_cookies()
    if not st.session_state.auth:
        st.warning("Silakan login terlebih dahulu.")
        st.page_link("app.py", label="Ke halaman Login", icon=":material/login:")
        st.stop()
    with st.sidebar:
        st.caption(f"Masuk sebagai: **{st.session_state.user}**")
        if st.button("Keluar", use_container_width=True):
            do_logout()
            st.switch_page("app.py")
