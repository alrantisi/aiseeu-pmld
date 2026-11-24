import io

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates

from utils.api import get_cameras, get_roi, get_snapshot, save_roi
from utils.auth import require_login
from utils.style import hero, inject_style

st.set_page_config(page_title="Setup ROI - AISeeU", layout="wide")
require_login()
inject_style()
hero("Setup Multi ROI", "")

# Gambar dirender 1400 px lalu ditampilkan selebar kolom (klik tetap akurat
# karena koordinat dinormalisasi memakai ukuran tampilan dari komponen).
DISPLAY_W = 1400
LINE_W = 4
DOT_R = 7
COLORS = ["#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"]

try:
    FONT = ImageFont.load_default(size=22)
    FONT_SM = ImageFont.load_default(size=18)
except Exception:  # Pillow tanpa dukungan ukuran font
    FONT = FONT_SM = ImageFont.load_default()

ss = st.session_state

if "flash" in ss:
    st.success(ss.pop("flash"))

cameras = get_cameras()
if not cameras:
    st.error("Tidak ada kamera dari backend, atau backend tidak bisa dihubungi.")
    st.stop()

cam = st.selectbox("Kamera", [c["camera_id"] for c in cameras])

pts_key = f"pts_{cam}"
snap_key = f"snap_{cam}"
click_key = f"lastclick_{cam}"
ver_key = f"ver_{cam}"
ss.setdefault(pts_key, [])
ss.setdefault(ver_key, 0)
ss.setdefault(click_key, None)

# Snapshot diambil sekali per kamera, lalu disimpan supaya klik tidak
# memicu pengambilan ulang tiap kali.
if ss.get(snap_key) is None:
    ss[snap_key] = get_snapshot(cam)
if ss[snap_key] is None:
    st.error("Gagal mengambil snapshot dari backend.")
    st.stop()

base = Image.open(io.BytesIO(ss[snap_key])).convert("RGB")
scale = DISPLAY_W / base.width
base = base.resize((DISPLAY_W, round(base.height * scale)))
W, H = base.size

zones = get_roi(cam)


def to_px(point):
    return (point[0] * W, point[1] * H)


def hex_to_rgba(color, alpha):
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)


from utils.zones import draw_zones


def render(saved_zones, draft_points):
    return draw_zones(base, saved_zones, draft_points)


@st.dialog("Hapus zone?")
def confirm_delete(zone, all_zones, camera_id):
    st.write(
        f"Zone **{zone['zone_name']}** akan dihapus dari konfigurasi dan tidak "
        "dihitung lagi."
    )
    a, b = st.columns(2)
    if a.button("Batal", use_container_width=True):
        st.rerun()
    if b.button("Ya, hapus zone", type="primary", use_container_width=True):
        remaining = [z for z in all_zones if z["zone_id"] != zone["zone_id"]]
        ok, msg = save_roi(camera_id, remaining)
        if ok:
            ss["flash"] = f"Zone {zone['zone_name']} dihapus."
            st.rerun()
        else:
            st.error(msg)


left, right = st.columns([3, 1])

with left:
    st.caption(
        "Klik di gambar untuk menambah titik sudut zona (minimal 3 titik), "
        "lalu isi nama dan klik Tambah zona."
    )
    click = streamlit_image_coordinates(
        render(zones, ss[pts_key]),
        key=f"img_{cam}_{ss[ver_key]}",
        use_column_width="always",
        image_format="JPEG",
        jpeg_quality=85,
    )
    if click:
        click_id = (click["x"], click["y"], click.get("unix_time"))
        if click_id != ss[click_key]:
            ss[click_key] = click_id
            x = min(max(click["x"] / click["width"], 0.0), 1.0)
            y = min(max(click["y"] / click["height"], 0.0), 1.0)
            ss[pts_key].append((x, y))
            st.rerun()

    name = st.text_input(
        "Nama zone",
        placeholder="Contoh: Kendaraan Masuk Gate A",
        key=f"name_{cam}_{ss[ver_key]}",
    )
    st.caption(f"Titik terpasang: {len(ss[pts_key])}")

    b1, b2, b3 = st.columns(3)
    if b1.button("Hapus titik terakhir", use_container_width=True):
        if ss[pts_key]:
            ss[pts_key].pop()
        st.rerun()
    if b2.button("Reset titik", use_container_width=True):
        ss[pts_key] = []
        ss[ver_key] += 1
        ss[click_key] = None
        st.rerun()
    if b3.button("Tambah zona", type="primary", use_container_width=True):
        clean_name = name.strip()
        used_names = [z["zone_name"].lower() for z in zones]
        if not clean_name:
            st.error("Isi nama zone terlebih dahulu.")
        elif clean_name.lower() in used_names:
            st.error("Nama zone harus unik pada satu kamera.")
        elif len(ss[pts_key]) < 3:
            st.error("Klik minimal 3 titik di gambar terlebih dahulu.")
        else:
            used_ids = {z["zone_id"] for z in zones}
            zone_id = next(
                f"Z{i}" for i in range(1, 100) if f"Z{i}" not in used_ids
            )
            new_zone = {
                "zone_id": zone_id,
                "zone_name": clean_name,
                "points": [[round(x, 4), round(y, 4)] for x, y in ss[pts_key]],
            }
            ok, msg = save_roi(cam, zones + [new_zone])
            if ok:
                ss[pts_key] = []
                ss[ver_key] += 1
                ss[click_key] = None
                ss["flash"] = f"Zone {clean_name} tersimpan sebagai {zone_id}."
                st.rerun()
            else:
                st.error(msg)

with right:
    st.subheader("Zone tersimpan")
    if not zones:
        st.caption("Belum ada zone.")
    for i, z in enumerate(zones):
        color = COLORS[i % len(COLORS)]
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(
                f"<span style='display:inline-block;width:12px;height:12px;"
                f"background:{color};border-radius:3px;margin-right:6px'></span>"
                f"{z['zone_name']}<br><small>{z['zone_id']} - "
                f"{len(z['points'])} titik</small>",
                unsafe_allow_html=True,
            )
            if c2.button(
                "Hapus",
                key=f"del_{cam}_{z['zone_id']}",
            ):
                confirm_delete(z, zones, cam)
