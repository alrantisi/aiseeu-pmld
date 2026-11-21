"""Mock data & helper untuk prototype AISeeU (tanpa backend / ML sungguhan)."""
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

W, H = 640, 360
VEHICLES = ["Mobil", "Motor", "Bus", "Truk"]
COLORS = ["#1f7ae0", "#e8a317", "#1f8a4c", "#c7382d", "#8e44ad", "#16a3a3"]

CAMERAS = {
    "CAM-01": {"name": "Kamera 1 - Gerbang Utama",
               "rtsp": "rtsp://192.168.1.20:554/stream1",
               "default_video": "/videos/gerbang_default.mp4"},
    "CAM-02": {"name": "Kamera 2 - Area Parkir",
               "rtsp": "rtsp://192.168.1.21:554/stream1",
               "default_video": "/videos/parkir_default.mp4"},
}


def _rgba(hex_color, alpha=255):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5)) + (alpha,)


def default_zones():
    return {
        "CAM-01": [
            {"zone_id": "Z1", "zone_name": "Kendaraan Masuk Gate A",
             "polygon": [(120, 300), (290, 300), (285, 200), (170, 200)], "color": COLORS[0]},
            {"zone_id": "Z2", "zone_name": "Kendaraan Keluar Gate A",
             "polygon": [(350, 300), (530, 300), (480, 200), (355, 200)], "color": COLORS[1]},
        ],
        "CAM-02": [
            {"zone_id": "Z1", "zone_name": "Area Parkir Motor",
             "polygon": [(60, 310), (300, 310), (300, 210), (90, 210)], "color": COLORS[2]},
        ],
    }


def init_state():
    ss = st.session_state
    ss.setdefault("auth", False)
    ss.setdefault("user", "")
    ss.setdefault("zones", default_zones())
    ss.setdefault("drafts", {c: [] for c in CAMERAS})
    ss.setdefault("counters", {})
    ss.setdefault("video_mode", "LIVE_CCTV")
    ss.setdefault("canvas_key", 0)
    ss.setdefault("cameras", {k: dict(v) for k, v in CAMERAS.items()})
    ss.setdefault("status_log", [{
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kamera": "CAM-01", "status": "LIVE_CCTV", "keterangan": "Koneksi RTSP berhasil"}])


def tick_counters(cam, zones):
    """Simulasi perubahan counter: current inside & total accumulated."""
    cnt = st.session_state.counters.setdefault(cam, {})
    for z in zones:
        c = cnt.setdefault(z["zone_id"], {"inside": random.randint(1, 6), "total": random.randint(80, 200)})
        c["total"] += random.choice([0, 0, 1, 1, 2])
        c["inside"] = max(0, min(15, c["inside"] + random.choice([-1, 0, 0, 1])))
    return cnt


def make_frame(zones, mode="LIVE_CCTV", boxes=True):
    """Gambar frame CCTV palsu: jalan, poligon ROI, dan bounding box kendaraan."""
    img = Image.new("RGBA", (W, H), (59, 70, 80, 255))
    d = ImageDraw.Draw(img)
    d.polygon([(230, H), (410, H), (360, 130), (290, 130)], fill=(43, 50, 57, 255))
    for y in range(140, H, 26):
        d.line([(320, y), (320, y + 14)], fill=(217, 217, 217, 255), width=3)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for z in zones:
        pts = [tuple(p) for p in z["polygon"]]
        if len(pts) >= 3:
            od.polygon(pts, fill=_rgba(z["color"], 70), outline=_rgba(z["color"]), width=3)
    img = Image.alpha_composite(img, overlay)
    d = ImageDraw.Draw(img)
    if boxes:
        for _ in range(random.randint(2, 4)):
            x, y, w = random.randint(140, 500), random.randint(190, 290), random.randint(40, 70)
            d.rectangle([x, y, x + w, y + int(w * .65)], outline=(255, 255, 255, 255), width=2)
            d.text((x, y - 12), f"{random.choice(VEHICLES).lower()} #{random.randint(10, 40)} "
                                f"{random.uniform(.8, .97):.2f}", fill=(255, 255, 255, 255))
    live = mode == "LIVE_CCTV"
    d.rectangle([8, 8, 190 if live else 250, 30], fill=(31, 138, 76, 255) if live else (232, 163, 23, 255))
    d.text((16, 14), "LIVE CCTV" if live else "DEMO MODE - DEFAULT_LOOP", fill=(255, 255, 255, 255))
    return img.convert("RGB")


@st.cache_data
def history_df(n=800):
    rng = np.random.default_rng(15)
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    times = [now - timedelta(minutes=int(m)) for m in rng.integers(0, 7 * 24 * 60, n)]
    zones = ["Kendaraan Masuk Gate A", "Kendaraan Keluar Gate A", "Area Parkir Motor"]
    df = pd.DataFrame({
        "waktu": times,
        "zone": rng.choice(zones, n),
        "jenis": rng.choice(VEHICLES, n, p=[.4, .45, .05, .1]),
        "confidence": rng.uniform(.6, .98, n).round(2),
        "sumber_video": rng.choice(["LIVE_CCTV", "DEFAULT_LOOP"], n, p=[.9, .1]),
    })
    df["arah"] = np.where(df["zone"].str.contains("Keluar"), "Keluar", "Masuk")
    return df.sort_values("waktu", ascending=False).reset_index(drop=True)
