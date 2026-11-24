# AISeeU: Multi Zone Vehicle Counting

Sistem penghitung kendaraan multi zona berbasis YOLO. Kendaraan dideteksi dan dilacak dari video (file atau CCTV), dihitung masuk/keluar pada zona ROI yang bisa digambar sendiri, lalu dicatat ke database dan ditampilkan di dashboard web.

Proyek PMLD, D4 UGM.

## Fitur

- Deteksi dan tracking kendaraan: bus, mobil, motor, truk (YOLOv8n hasil fine-tune)
- Multi ROI: gambar beberapa zona per kamera langsung di gambar snapshot, hitung masuk (ENTER) dan keluar (EXIT) per zona
- Dashboard real time: video MJPEG dengan bounding box, hitungan per jenis kendaraan dan per zona, zona ROI bisa ditampilkan di atas video
- Histori dan pelaporan: filter zona, jenis, aksi, dan tanggal; grafik; tabel; ekspor CSV; hapus log selektif (admin)
- Video Source Manager: tambah dan hapus kamera, pindah sumber `LIVE_CCTV` (RTSP/HLS) atau `DEFAULT_LOOP` (file video)
- Login berbasis sesi; semua endpoint `/api/` wajib login (kecuali `/api/auth/*` dan `/feed`); hapus log dan hapus kamera hanya untuk admin

## Arsitektur

```
Browser
  |  :8501
  v
Streamlit (frontend)
  |  HTTP + cookie sesi
  v
Flask + gunicorn (backend)  :5000
  |-- routes: auth, camera, roi, log
  |-- ml_engine: YOLO + tracking + logika zona
  |-- sumber video: LIVE_CCTV (RTSP/HLS) / DEFAULT_LOOP (mp4)
  v
PostgreSQL  :5432
  |-- pmld_management  (users, camera_sources, roi_configurations)
  |-- pmld_data        (vehicle_logs)
```

## Teknologi

| Lapisan | Teknologi |
|---|---|
| Backend | Python 3.11, Flask, Flask-SQLAlchemy, gunicorn |
| Deteksi | Ultralytics YOLO, PyTorch (CPU), OpenCV headless |
| Frontend | Python 3.12, Streamlit, pandas, streamlit-image-coordinates |
| Database | PostgreSQL 18 |
| Deploy | Ubuntu Server, systemd, uv |

## Struktur repositori

```
backend/
  app/            Flask app (config, extensions, routes/, models/, services/, middleware/)
  ml_engine/      detektor kendaraan, tracking, logika zona
  run.py          entry point (gunicorn run:app)
  create_tables.py, create_admin.py
  requirements.txt
frontend/
  app.py          halaman utama + login
  pages/          Dashboard, Setup ROI, Histori & Pelaporan, Video Source Manager
  utils/          api.py, auth.py, style.py, zones.py
  .streamlit/     konfigurasi tema
  requirements.txt
```

File yang sengaja **tidak** ada di repo: `.env`, `venv/`, model `*.pt`, dan video `*.mp4` (lihat `.gitignore`).

## Prasyarat

- Ubuntu Server (diuji di 26.04), PostgreSQL, [uv](https://docs.astral.sh/uv/)
- File model YOLO (`best.pt`) dan satu video uji, diletakkan manual di server
- Opsional: Docker + mediamtx dan ffmpeg untuk simulasi RTSP

## Instalasi

### 1. Database

Buat user dan dua database (`pmld_management`, `pmld_data`) di PostgreSQL, dengan password yang kuat:

```bash
sudo -u postgres psql
CREATE USER pmld_user WITH PASSWORD '<password-kuat>';
CREATE DATABASE pmld_management OWNER pmld_user;
CREATE DATABASE pmld_data OWNER pmld_user;
```

### 2. Backend

```bash
cd backend
uv venv --python 3.11 venv
uv pip install --python venv/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python venv/bin/python -r requirements.txt
```

Buat file `backend/.env` (jangan di-commit) dengan variabel berikut:

| Variabel | Fungsi |
|---|---|
| `MANAGEMENT_DATABASE_URL` | Koneksi ke `pmld_management` |
| `DATA_DATABASE_URL` | Koneksi ke `pmld_data` |
| `SECRET_KEY` | Kunci penanda tangan sesi login (acak, 64 hex) |
| `YOLO_MODEL_PATH` | Lokasi file model `.pt` |
| `YOLO_CONFIDENCE` | Ambang confidence (contoh: `0.25`) |

Membuat `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Buat tabel dan akun admin, **lalu langsung ganti password admin**:

```bash
venv/bin/python create_tables.py
venv/bin/python create_admin.py
```

Jalankan:

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 venv/bin/gunicorn -w 1 --threads 8 --timeout 0 -b 0.0.0.0:5000 run:app
```

Catatan: pakai `-w 1` karena state tracking disimpan di memori proses. Jangan menjalankan dengan `debug=True`.

### 3. Frontend

```bash
cd frontend
uv venv --python 3.12 venv
uv pip install --python venv/bin/python -r requirements.txt
venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

Alamat backend diatur di `frontend/utils/api.py` (`BASE_URL`). Dashboard dibuka di `http://<alamat-server>:8501`.

### 4. Jalan otomatis (systemd)

Daftarkan dua service: `pmld` (backend, di atas `postgresql`) dan `pmld-frontend` (setelah `pmld`), masing-masing dengan `Restart=always`, lalu aktifkan:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pmld pmld-frontend
```

Service backend perlu variabel lingkungan `PYTHONUNBUFFERED=1` dan `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`.

## Port

| Port | Layanan |
|---|---|
| 5000 | Backend API |
| 8501 | Frontend Streamlit |
| 5432 | PostgreSQL (sebaiknya hanya localhost) |

## API ringkas

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/check` | Cek sesi |
| GET, POST | `/api/cameras` | Daftar dan tambah kamera |
| PUT | `/api/cameras/<id>/source` | Ubah sumber video |
| GET | `/api/cameras/<id>/snapshot` | Satu frame JPEG |
| GET | `/api/cameras/<id>/feed` | Stream MJPEG dengan deteksi |
| GET | `/api/cameras/<id>/detections` | Hitungan deteksi saat ini |
| GET, POST | `/api/cameras/<id>/roi` | Ambil dan simpan zona ROI |
| GET | `/api/logs`, `/api/logs/summary` | Log kendaraan dan rekap |

Ada juga endpoint khusus admin untuk hapus kamera, hapus log, dan reset counter.

## Catatan penggunaan

- Satu kamera hanya satu stream `/feed` pada satu waktu. Setelah mengubah ROI atau sumber video, buka ulang Dashboard.
- Zona ROI tidak boleh tumpang tindih (zona pertama yang menang).
- Request `/feed` pertama setelah restart lambat karena YOLO berjalan di CPU.
- Waktu di backend UTC; frontend menampilkan WIB.

## Keterbatasan yang diketahui

- Hanya HTTP, belum ada HTTPS
- `/feed` dapat diakses tanpa login (karena dimuat lewat tag `<img>`)
- Satu worker gunicorn dan inferensi di CPU, sehingga kapasitas terbatas
- Belum ada backup database terjadwal dan belum ada reconnect otomatis untuk `LIVE_CCTV`
- Memori naik pelan pada stream yang berjalan lama (`seen_ids` tidak dibersihkan)
- Akurasi motor dan klasifikasi mobil/truk masih kurang (akar masalah: data latih)
- Halaman Histori hanya memuat 5.000 log terbaru

## Keamanan

- Jangan commit `.env`, password, atau token. Gunakan password yang kuat dan unik untuk database dan akun admin, serta ganti password bawaan setelah instalasi.
- Batasi PostgreSQL ke `localhost` dan gunakan firewall untuk port yang tidak perlu dibuka.

## Tim

Tulis nama anggota tim di sini.
