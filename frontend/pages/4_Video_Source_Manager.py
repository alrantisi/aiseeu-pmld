import pandas as pd
import streamlit as st

from utils.api import create_camera, get_cameras, update_camera_source
from utils.auth import require_login

st.set_page_config(page_title="Video Source Manager - AISeeU", layout="wide")
require_login()

st.title("Video Source Manager & Pengaturan")
st.caption("Data dari backend. Perubahan sumber video berlaku saat stream dibuka ulang (buka ulang Dashboard).")

MODES = ["LIVE_CCTV", "DEFAULT_LOOP"]


def to_wib(value):
    """Ubah waktu dari backend (UTC) ke WIB. Return '-' kalau kosong."""
    if not value:
        return "-"
    try:
        ts = pd.to_datetime(value, utc=True).tz_convert("Asia/Jakarta")
        return ts.strftime("%Y-%m-%d %H:%M:%S WIB")
    except (ValueError, TypeError):
        return str(value)


# Pesan sukses disimpan dulu supaya tetap tampil setelah halaman dimuat ulang
flash = st.session_state.pop("vsm_flash", None)
if flash:
    st.success(flash)

with st.expander("Tambah kamera baru"):
    with st.form("add_camera", clear_on_submit=True):
        new_id = st.text_input("ID kamera (contoh: CAM02)")
        new_rtsp = st.text_input("RTSP / HLS URL (boleh kosong)")
        new_video = st.text_input(
            "Path video default (fallback)",
            "/home/alran/pmld/backend/videos/camera_test.mp4",
        )
        add = st.form_submit_button("Tambah kamera")
    if add:
        if not new_id.strip() or not new_video.strip():
            st.error("ID kamera dan path video default wajib diisi.")
        else:
            ok, message = create_camera(
                new_id.strip(), new_rtsp.strip(), new_video.strip()
            )
            if ok:
                st.session_state["vsm_flash"] = message
                st.rerun()
            else:
                st.error(message)

cameras = get_cameras()
if not cameras:
    st.error("Daftar kamera tidak bisa diambil dari backend (atau belum ada kamera terdaftar).")
    st.stop()

by_id = {c["camera_id"]: c for c in cameras}
camera_id = st.selectbox("Kamera", list(by_id))
cam = by_id[camera_id]

left, right = st.columns([3, 2])

with left:
    with st.form(f"cfg_{camera_id}"):
        rtsp = st.text_input("RTSP URL", cam.get("rtsp_url") or "")
        video = st.text_input(
            "Path video default (fallback)", cam.get("default_video_path") or ""
        )
        current = cam.get("current_source")
        mode = st.radio(
            "Sumber video aktif",
            MODES,
            index=MODES.index(current) if current in MODES else 1,
            horizontal=True,
        )
        submitted = st.form_submit_button("Simpan perubahan", type="primary")

    if submitted:
        ok, message = update_camera_source(
            camera_id,
            rtsp_url=rtsp.strip(),
            default_video_path=video.strip(),
            current_source=mode,
        )
        if ok:
            st.session_state["vsm_flash"] = message
            st.rerun()
        else:
            st.error(message)

with right:
    with st.container(border=True):
        st.markdown("**Status sumber video**")
        st.metric("Sumber aktif", cam.get("current_source") or "-")
        st.caption(f"Terakhir dicek: {to_wib(cam.get('last_checked_at'))}")
        st.caption(f"Terakhir online (LIVE_CCTV): {to_wib(cam.get('last_online_at'))}")
