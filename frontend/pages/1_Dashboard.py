import streamlit as st

from utils.api import BASE_URL, get_cameras, get_detections, reset_counter
from utils.auth import require_login

st.set_page_config(page_title="Dashboard - AISeeU", layout="wide")
require_login()

st.title("Dashboard Real Time")

cameras = get_cameras()
if not cameras:
    st.error("Tidak ada kamera dari backend, atau backend tidak bisa dihubungi.")
    st.stop()

cam = st.selectbox("Kamera", [c["camera_id"] for c in cameras])
auto = st.toggle("Perbarui angka otomatis (tiap 2 detik)", value=True)

left, right = st.columns([2, 1])

# Video langsung dari backend (MJPEG). Dibiarkan di luar fragment supaya
# tidak ikut dimuat ulang setiap 2 detik.
with left:
    st.markdown(
        f'<img src="{BASE_URL}/api/cameras/{cam}/feed" '
        'style="width:100%;aspect-ratio:16/9;object-fit:contain;background:#111;border-radius:8px">',
        unsafe_allow_html=True,
    )
    st.caption("Frame pertama bisa butuh beberapa detik (YOLO jalan di CPU).")


def panel():
    data = get_detections(cam)
    if data is None:
        st.warning("Gagal mengambil data deteksi dari backend.")
        return

    if data.get("error"):
        st.warning(f"Backend melaporkan: {data['error']}")

    st.markdown("**Kendaraan unik sejak stream dimulai** (reset saat service direstart)")
    a, b = st.columns(2)
    a.metric("Mobil", data.get("car", 0))
    b.metric("Motor", data.get("motorcycle", 0))
    c, d = st.columns(2)
    c.metric("Bus", data.get("bus", 0))
    d.metric("Truk", data.get("truck", 0))

    st.markdown("**Hitungan per zona**")
    zone_counts = data.get("zone_counts", {})
    if not zone_counts:
        st.info("Belum ada zona. Buat di menu Setup ROI.")
        return

    for zone_id, z in zone_counts.items():
        with st.container(border=True):
            color = z.get("color", "#888888")
            st.markdown(
                f"<span style='display:inline-block;width:12px;height:12px;"
                f"background:{color};border-radius:3px;margin-right:6px'></span>"
                f"**{z.get('name', zone_id)}**",
                unsafe_allow_html=True,
            )
            m1, m2, m3 = st.columns(3)
            m1.metric("Masuk", z.get("in", 0))
            m2.metric("Keluar", z.get("out", 0))
            m3.metric("Total", z.get("total", 0))


with right:
    if st.button("Reset counter", use_container_width=True):
        ok, msg = reset_counter(cam)
        if ok:
            st.toast(msg)
        else:
            st.error(msg)
    if auto:
        st.fragment(run_every=2)(panel)()
    else:
        panel()
        st.button("Perbarui sekarang")
