import pandas as pd
import streamlit as st

from utils.api import delete_logs, get_cameras, get_logs, get_logs_summary
from utils.auth import require_login
from utils.style import hero, inject_style

st.set_page_config(page_title="Histori - AISeeU", layout="wide")
require_login()
inject_style()

hero("Histori & Pelaporan", "Riwayat kejadian dan rekap kendaraan per kamera")
st.caption("Data dari backend. Waktu ditampilkan dalam WIB.")

cameras = get_cameras()
if not cameras:
    st.error("Tidak ada kamera dari backend, atau backend tidak bisa dihubungi.")
    st.stop()

cam = st.selectbox("Kamera", [c["camera_id"] for c in cameras])
flash = st.session_state.pop("hist_flash", None)
if flash:
    st.success(flash)

# ---- Rekap keseluruhan (dihitung backend) ----
summary = get_logs_summary(cam)
if summary:
    counts = summary.get("vehicle_counts", {})
    activity = summary.get("activity_counts", {})
    st.markdown("**Rekap keseluruhan (kendaraan unik)**")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total kendaraan", summary.get("total_unique_vehicles", 0))
    k2.metric("Mobil", counts.get("Mobil", 0))
    k3.metric("Motor", counts.get("Motor", 0))
    k4.metric("Bus", counts.get("Bus", 0))
    k5.metric("Truk", counts.get("Truk", 0))
    k6.metric(
        "Masuk / Keluar",
        f"{activity.get('ENTER', 0)} / {activity.get('EXIT', 0)}",
    )
else:
    st.warning("Gagal mengambil rekap dari backend.")

# ---- Log detail ----
logs = get_logs(cam)
if not logs:
    st.info("Belum ada log untuk kamera ini.")
    st.stop()

df = pd.DataFrame(logs).rename(
    columns={
        "camera_id": "kamera",
        "zone_name": "zone",
        "vehicle_type": "jenis",
        "action": "aksi",
        "source_type": "sumber_video",
    }
)
df["waktu"] = (
    pd.to_datetime(df["created_at"])
    .dt.tz_localize("UTC")
    .dt.tz_convert("Asia/Jakarta")
)
df = df.dropna(subset=["waktu"])

if len(logs) >= 5000:
    st.caption("Hanya 5.000 log terbaru yang dimuat.")

with st.container(border=True):
    c1, c2, c3, c4 = st.columns(4)
    zone = c1.multiselect("Zone", sorted(df["zone"].dropna().unique()))
    jenis = c2.multiselect("Jenis kendaraan", sorted(df["jenis"].dropna().unique()))
    aksi = c3.multiselect("Aksi", ["ENTER", "EXIT"])
    rng = c4.date_input(
        "Rentang tanggal",
        (df["waktu"].dt.date.min(), df["waktu"].dt.date.max()),
    )

f = df
if zone:
    f = f[f["zone"].isin(zone)]
if jenis:
    f = f[f["jenis"].isin(jenis)]
if aksi:
    f = f[f["aksi"].isin(aksi)]
if isinstance(rng, tuple) and len(rng) == 2:
    f = f[(f["waktu"].dt.date >= rng[0]) & (f["waktu"].dt.date <= rng[1])]

m1, m2, m3 = st.columns(3)
m1.metric("Total event (ENTER + EXIT)", len(f))
m2.metric("Rata-rata confidence", f"{f['confidence'].mean():.2f}" if len(f) else "-")
m3.metric("Event dari DEFAULT_LOOP", int((f["sumber_video"] == "DEFAULT_LOOP").sum()))

if f.empty:
    st.info("Tidak ada data untuk filter ini.")
    st.stop()

g1, g2 = st.columns(2)
with g1:
    st.markdown("**Aktivitas per hari per zone**")
    st.bar_chart(
        f.assign(tanggal=f["waktu"].dt.date).pivot_table(
            index="tanggal",
            columns="zone",
            values="id",
            aggfunc="count",
            fill_value=0,
        )
    )
with g2:
    st.markdown("**Tren per jam (WIB)**")
    st.line_chart(f.groupby(f["waktu"].dt.hour).size().rename("jumlah"))

st.markdown("**Tabel histori**")
table = f[
    ["waktu", "kamera", "zone", "jenis", "aksi", "track_id", "confidence", "sumber_video"]
].assign(waktu=f["waktu"].dt.strftime("%Y-%m-%d %H:%M:%S"))
st.dataframe(table, use_container_width=True, hide_index=True)
st.download_button(
    "Ekspor CSV",
    table.to_csv(index=False).encode("utf-8"),
    "histori_counting.csv",
    "text/csv",
)


@st.dialog("Hapus log yang sedang ditampilkan?")
def confirm_delete_logs(camera_id, ids, filter_text):
    st.write(
        f"**{len(ids)}** event log kamera **{camera_id}** akan dihapus "
        "permanen dan tidak bisa dikembalikan."
    )
    st.caption(f"Sesuai filter aktif: {filter_text}")
    typed = st.text_input(f"Ketik {camera_id} lalu tekan Enter untuk konfirmasi")
    a, b = st.columns(2)
    if a.button("Batal", use_container_width=True):
        st.rerun()
    if b.button(
        "Ya, hapus log",
        type="primary",
        use_container_width=True,
        disabled=typed.strip() != camera_id,
    ):
        ok, msg = delete_logs(camera_id, ids)
        if ok:
            st.session_state["hist_flash"] = msg
            st.rerun()
        else:
            st.error(msg)


st.divider()
with st.expander("Hapus data log (sesuai filter di atas)"):
    st.caption(
        "Yang dihapus hanya event yang sedang tampil di tabel, jadi atur "
        "filter Zone, Jenis kendaraan, Aksi, dan Rentang tanggal dulu. "
        "Angka di Dashboard tidak ikut ter-reset."
    )
    parts = [
        "zone: " + (", ".join(zone) if zone else "semua"),
        "jenis: " + (", ".join(jenis) if jenis else "semua"),
        "aksi: " + (", ".join(aksi) if aksi else "semua"),
    ]
    if isinstance(rng, tuple) and len(rng) == 2:
        parts.append(f"tanggal: {rng[0]} s/d {rng[1]}")
    filter_text = " | ".join(parts)
    st.write(f"Akan dihapus: **{len(f)}** event ({filter_text})")
    if st.button("Hapus log sesuai filter", key="open_del_logs"):
        confirm_delete_logs(cam, [int(i) for i in f["id"]], filter_text)
