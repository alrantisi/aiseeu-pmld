import html
import io

import streamlit as st
from PIL import Image

from utils.api import BASE_URL, get_cameras, get_detections, get_roi, get_snapshot, reset_counter
from utils.auth import require_login
from utils.style import hero, inject_style

st.set_page_config(page_title="Dashboard - AISeeU", layout="wide")
require_login()
inject_style()

hero("Dashboard Real Time", "Pantau video dan hitungan kendaraan langsung dari kamera")

cameras = get_cameras()
if not cameras:
    st.error("Tidak ada kamera dari backend, atau backend tidak bisa dihubungi.")
    st.stop()

k1, k2, k3 = st.columns([3, 2, 1])
with k1:
    cam = st.selectbox("Kamera", [c["camera_id"] for c in cameras])
with k2:
    st.write("")
    auto = st.toggle("Perbarui angka otomatis (tiap 2 detik)", value=True)
with k3:
    st.write("")
    if st.button("Reset counter", use_container_width=True):
        ok, msg = reset_counter(cam)
        if ok:
            st.toast(msg)
        else:
            st.error(msg)


def top_panel():
    data = get_detections(cam)
    if data is None:
        st.warning("Gagal mengambil data deteksi dari backend.")
        return
    if data.get("error"):
        st.warning(f"Backend melaporkan: {data['error']}")
    st.caption("Kendaraan unik sejak stream dimulai (reset saat service direstart)")
    cols = st.columns(5)
    total = data.get("total")
    if total is None:
        total = sum(data.get(k, 0) for k in ("car", "motorcycle", "bus", "truck"))
    cols[0].metric("Total", total)
    cols[1].metric("Mobil", data.get("car", 0))
    cols[2].metric("Motor", data.get("motorcycle", 0))
    cols[3].metric("Bus", data.get("bus", 0))
    cols[4].metric("Truk", data.get("truck", 0))


def zone_panel():
    data = get_detections(cam)
    if data is None:
        return
    st.subheader("Hitungan per zona")
    zone_counts = data.get("zone_counts", {})
    if not zone_counts:
        st.info("Belum ada zona. Buat di menu Setup ROI.")
        return
    items = list(zone_counts.items())
    for start in range(0, len(items), 3):
        cols = st.columns(3)
        for col, (zone_id, z) in zip(cols, items[start:start + 3]):
            with col:
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


def render(panel):
    if auto:
        st.fragment(run_every=2)(panel)()
    else:
        panel()


FALLBACK_COLORS = ["#06b6d4", "#f59e0b", "#22c55e", "#ef4444", "#a855f7", "#ec4899"]


@st.cache_data(ttl=30, show_spinner=False)
def frame_and_zones(camera_id):
    """Ukuran frame asli (dari satu snapshot) dan daftar zona ROI.

    Ukuran dipakai supaya overlay SVG punya rasio yang sama dengan video,
    jadi zona tetap pas walaupun ada pita gelap di kiri/kanan atau atas/bawah.
    """
    width, height = 1920, 1080  # cadangan kalau snapshot gagal
    raw = get_snapshot(camera_id)
    if raw:
        try:
            width, height = Image.open(io.BytesIO(raw)).size
        except Exception:
            pass
    return width, height, get_roi(camera_id) or []


def build_overlay(width, height, zones, colors):
    """SVG transparan berisi poligon dan nama zona (titik zona 0..1)."""
    parts = []
    font = height * 0.034
    halo = height * 0.007
    for i, zone in enumerate(zones):
        points = zone.get("points") or []
        if len(points) < 3:
            continue
        zone_id = zone.get("zone_id", "")
        color = colors.get(zone_id) or FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
        name = html.escape(str(zone.get("zone_name") or zone_id))
        pts = " ".join(f"{p[0] * width:.1f},{p[1] * height:.1f}" for p in points)
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        cx = min(max(cx, 0.06), 0.94) * width
        cy = min(max(cy, 0.06), 0.94) * height
        parts.append(
            f'<polygon points="{pts}" fill="{color}" fill-opacity="0.18" '
            f'stroke="{color}" stroke-width="3" vector-effect="non-scaling-stroke"/>'
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-family="sans-serif" font-weight="700" font-size="{font:.1f}" fill="#ffffff" '
            f'stroke="#000000" stroke-opacity="0.75" stroke-width="{halo:.1f}" '
            f'paint-order="stroke" stroke-linejoin="round">{name}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" '
        'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
        + "".join(parts)
        + "</svg>"
    )


render(top_panel)

show_zones = st.toggle(
    "Tampilkan zona ROI di atas video",
    value=False,
    help="Menyalakan atau mematikan ini membuka ulang stream (butuh beberapa detik).",
)

overlay = ""
if show_zones:
    fw, fh, zones = frame_and_zones(cam)
    if zones:
        detections = get_detections(cam) or {}
        colors = {
            zid: z.get("color")
            for zid, z in (detections.get("zone_counts") or {}).items()
            if z.get("color")
        }
        overlay = build_overlay(fw, fh, zones, colors)
    else:
        st.info("Belum ada zona untuk kamera ini. Buat di menu Setup ROI.")

# Video langsung dari backend (MJPEG). Dibiarkan di luar fragment supaya
# tidak ikut dimuat ulang setiap 2 detik. HTML dibuat satu baris supaya
# tidak dianggap blok kode oleh markdown.
st.markdown(
    '<div style="position:relative;width:100%;aspect-ratio:16/9;background:#0a0f14;'
    'border-radius:14px;overflow:hidden;margin:6px 0 4px 0">'
    f'<img src="{BASE_URL}/api/cameras/{cam}/feed" '
    'style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain">'
    f"{overlay}</div>",
    unsafe_allow_html=True,
)
st.caption("Frame pertama bisa butuh beberapa detik (YOLO jalan di CPU).")

render(zone_panel)

if not auto:
    st.button("Perbarui sekarang")
