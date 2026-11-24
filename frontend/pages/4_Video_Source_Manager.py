import pandas as pd
import streamlit as st

from utils.api import (
    create_camera,
    delete_camera,
    get_cameras,
    get_roi,
    update_camera_source,
)
from utils.auth import require_login
from utils.style import hero, inject_style

st.set_page_config(page_title="Video Source Manager - AISeeU", layout="wide")
require_login()
inject_style()

hero("Video Source Manager & Pengaturan", "Kelola sumber video semua kamera")
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


@st.dialog("Hapus kamera?")
def confirm_delete_camera(camera_id):
    st.write(
        f"Kamera **{camera_id}** dan konfigurasi ROI-nya akan dihapus. "
        "Log histori kamera ini tetap tersimpan. "
        "Tindakan ini tidak dapat dibatalkan."
    )
    typed = st.text_input(f"Ketik {camera_id} untuk konfirmasi")
    a, b = st.columns(2)
    if a.button("Batal", use_container_width=True):
        st.rerun()
    if b.button("Ya, hapus kamera", type="primary", use_container_width=True):
        if typed.strip() != camera_id:
            st.error("ID kamera tidak cocok. Penghapusan dibatalkan.")
        else:
            ok, message = delete_camera(camera_id)
            if ok:
                st.session_state["vsm_flash"] = message
                st.rerun()
            else:
                st.error(message)


# Pesan sukses disimpan dulu supaya tetap tampil setelah halaman dimuat ulang
flash = st.session_state.pop("vsm_flash", None)
if flash:
    st.success(flash)

cameras = get_cameras()

# --- Kartu status + tabel ringkas semua kamera -------------------------------
if cameras:
    zone_count = {}
    for c in cameras:
        zone_count[c["camera_id"]] = len(get_roi(c["camera_id"]) or [])

    n_live = sum(1 for c in cameras if c.get("current_source") == "LIVE_CCTV")
    n_loop = sum(1 for c in cameras if c.get("current_source") == "DEFAULT_LOOP")

    s1, s2, s3, s4 = st.columns(4)
    for col, label, value in (
        (s1, "Kamera terdaftar", len(cameras)),
        (s2, "Sumber LIVE_CCTV", n_live),
        (s3, "Sumber DEFAULT_LOOP", n_loop),
        (s4, "Total zona ROI", sum(zone_count.values())),
    ):
        with col:
            with st.container(border=True):
                st.metric(label, value)

    st.subheader("Ringkasan semua kamera")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Kamera": c["camera_id"],
                    "Sumber aktif": c.get("current_source") or "-",
                    "Zona": zone_count.get(c["camera_id"], 0),
                    "Terakhir dicek": to_wib(c.get("last_checked_at")),
                    "Terakhir online (LIVE)": to_wib(c.get("last_online_at")),
                }
                for c in cameras
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

# --- Tambah kamera (selalu tersedia, termasuk saat belum ada kamera) ---------
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

if not cameras:
    st.error("Daftar kamera tidak bisa diambil dari backend (atau belum ada kamera terdaftar).")
    st.stop()

# --- Pengaturan satu kamera ---------------------------------------------------
st.subheader("Pengaturan kamera")

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
        st.caption(f"Zona ROI terpasang: {zone_count.get(camera_id, 0)}")
        st.caption(f"Terakhir dicek: {to_wib(cam.get('last_checked_at'))}")
        st.caption(f"Terakhir online (LIVE_CCTV): {to_wib(cam.get('last_online_at'))}")

    with st.container(border=True):
        st.markdown("**Zona berbahaya**")
        st.caption("Hapus kamera beserta ROI-nya. Log histori tidak ikut terhapus.")
        if st.button(
            "Hapus kamera",
            key=f"del_cam_{camera_id}",
            use_container_width=True,
        ):
            confirm_delete_camera(camera_id)
