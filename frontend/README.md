# AISeeU: Multi Zone Vehicle Counting Dashboard - Prototype UI (Streamlit)

Prototype front-end berbasis **mock data** untuk SRS Kelompok 15. Tidak ada backend, database, kamera,
atau model AI sungguhan: semua angka, tabel, dan video adalah data dummy untuk keperluan demonstrasi UI.

## Cara menjalankan
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Buka http://localhost:8501. Login memakai akun admin dari backend (dibuat lewat `create_admin.py`).

## Struktur
```
aiseeu_streamlit/
├── app.py                          # Login + halaman utama
├── pages/
│   ├── 1_Dashboard.py              # Dashboard Real Time
│   ├── 2_Setup_ROI.py              # Setup Multi ROI (canvas poligon)
│   ├── 3_Histori_Laporan.py        # Histori & Pelaporan
│   └── 4_Video_Source_Manager.py   # Video Source Manager & Pengaturan
├── utils/
│   ├── auth.py                     # Guard login (mock)
│   └── mock_data.py                # Data dummy, frame CCTV palsu, state
├── .streamlit/config.toml          # Tema
├── requirements.txt
└── README.md
```

## Pemetaan ke SRS
| SRS | Implementasi |
|---|---|
| 3.1 Login | `app.py` (form, validasi, pesan error) |
| 3.2 Setup Multi ROI | `2_Setup_ROI.py` (pilih kamera, snapshot, gambar poligon, nama unik, banyak ROI, simpan, muat ulang, konfirmasi hapus sesuai 5.2) |
| 3.3 Video Source Manager | `4_Video_Source_Manager.py` (RTSP/default, simulasi LIVE_CCTV <-> DEFAULT_LOOP, log perubahan status) |
| 3.4 / 3.5 Deteksi & Counting | Disimulasikan: bounding box + counter per zone di `1_Dashboard.py` |
| 3.6 Dashboard Real Time | `1_Dashboard.py` (counter dinamis per zone, badge LIVE/DEMO, FPS, CPU/GPU, auto-update) |
| 3.7 Histori & Pelaporan | `3_Histori_Laporan.py` (filter zone/tanggal/jenis, tabel, grafik, ekspor CSV) |
| 3.8 Pengaturan Sistem | `4_Video_Source_Manager.py` (form kamera, status kesehatan layanan) |

## Catatan
- Data bersifat sementara (session): refresh browser mengembalikan data awal.
- Pada sistem asli: komunikasi real time via WebSocket dan grafik via Apache Superset; di prototype
  keduanya digantikan auto-refresh Streamlit dan chart bawaan.
- Versi Streamlit dipin ke 1.38.0 karena `streamlit-drawable-canvas` belum kompatibel dengan versi lebih baru.
  Jika canvas gagal tampil, halaman Setup ROI otomatis memakai input koordinat manual.
