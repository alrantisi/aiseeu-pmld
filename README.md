# AISeeU: Multi Zone Vehicle Counting

A multi-zone vehicle counting system built on YOLO. Vehicles are detected and tracked from video (a file or a CCTV stream), counted as they enter and exit user-defined ROI zones, stored in a database, and shown in a web dashboard.

PMLD project, D4 UGM.

## Features

- Vehicle detection and tracking: bus, car, motorcycle, truck (fine-tuned YOLOv8n)
- Multi-ROI: draw several zones per camera directly on a snapshot, and count entries (ENTER) and exits (EXIT) per zone
- Real-time dashboard: MJPEG video with bounding boxes, counts per vehicle type and per zone, and ROI zones that can be overlaid on the live video
- History and reporting: filter by zone, vehicle type, action, and date; charts; table; CSV export; selective log deletion (admin)
- Video Source Manager: add and delete cameras, switch the source between `LIVE_CCTV` (RTSP/HLS) and `DEFAULT_LOOP` (video file)
- Session-based login; every `/api/` endpoint requires login (except `/api/auth/*` and `/feed`); deleting logs and deleting cameras is admin-only

## Architecture

```
Browser
  |  :8501
  v
Streamlit (frontend)
  |  HTTP + session cookie
  v
Flask + gunicorn (backend)  :5000
  |-- routes: auth, camera, roi, log
  |-- ml_engine: YOLO + tracking + zone logic
  |-- video source: LIVE_CCTV (RTSP/HLS) / DEFAULT_LOOP (mp4)
  v
PostgreSQL  :5432
  |-- pmld_management  (users, camera_sources, roi_configurations)
  |-- pmld_data        (vehicle_logs)
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask, Flask-SQLAlchemy, gunicorn |
| Detection | Ultralytics YOLO, PyTorch (CPU), OpenCV headless |
| Frontend | Python 3.12, Streamlit, pandas, streamlit-image-coordinates |
| Database | PostgreSQL 18 |
| Deployment | Ubuntu Server, systemd, uv |

## Repository structure

```
backend/
  app/            Flask app (config, extensions, routes/, models/, services/, middleware/)
  ml_engine/      vehicle detector, tracking, zone logic
  run.py          entry point (gunicorn run:app)
  create_tables.py, create_admin.py
  requirements.txt
frontend/
  app.py          home page + login
  pages/          Dashboard, Setup ROI, History & Reports, Video Source Manager
  utils/          api.py, auth.py, style.py, zones.py
  .streamlit/     theme configuration
  requirements.txt
```

Files intentionally **not** in the repository: `.env`, `venv/`, model files (`*.pt`), and videos (`*.mp4`). See `.gitignore`.

## Prerequisites

- Ubuntu Server (tested on 26.04), PostgreSQL, [uv](https://docs.astral.sh/uv/)
- A YOLO model file (`best.pt`) and a test video, placed manually on the server
- Optional: Docker with mediamtx and ffmpeg to simulate an RTSP stream

## Installation

### 1. Database

Create a user and two databases (`pmld_management`, `pmld_data`) in PostgreSQL, using a strong password:

```bash
sudo -u postgres psql
CREATE USER pmld_user WITH PASSWORD '<strong-password>';
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

Create `backend/.env` (never commit it) with these variables:

| Variable | Purpose |
|---|---|
| `MANAGEMENT_DATABASE_URL` | Connection string for `pmld_management` |
| `DATA_DATABASE_URL` | Connection string for `pmld_data` |
| `SECRET_KEY` | Key used to sign login sessions (random, 64 hex characters) |
| `YOLO_MODEL_PATH` | Location of the `.pt` model file |
| `YOLO_CONFIDENCE` | Confidence threshold (for example `0.25`) |

Generate a `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Create the tables and the admin account, **then change the admin password right away**:

```bash
venv/bin/python create_tables.py
venv/bin/python create_admin.py
```

Run:

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 venv/bin/gunicorn -w 1 --threads 8 --timeout 0 -b 0.0.0.0:5000 run:app
```

Note: use `-w 1` because tracking state is kept in process memory. Do not run with `debug=True`.

### 3. Frontend

```bash
cd frontend
uv venv --python 3.12 venv
uv pip install --python venv/bin/python -r requirements.txt
venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

The backend address is set in `frontend/utils/api.py` (`BASE_URL`). Open the dashboard at `http://<server-address>:8501`.

### 4. Start on boot (systemd)

Register two services: `pmld` (backend, started after `postgresql`) and `pmld-frontend` (started after `pmld`), both with `Restart=always`, then enable them:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pmld pmld-frontend
```

The backend service needs the environment variables `PYTHONUNBUFFERED=1` and `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`.

## Ports

| Port | Service |
|---|---|
| 5000 | Backend API |
| 8501 | Streamlit frontend |
| 5432 | PostgreSQL (ideally localhost only) |

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Log in |
| GET | `/api/auth/check` | Check session |
| GET, POST | `/api/cameras` | List and add cameras |
| PUT | `/api/cameras/<id>/source` | Change video source |
| GET | `/api/cameras/<id>/snapshot` | Single JPEG frame |
| GET | `/api/cameras/<id>/feed` | MJPEG stream with detections |
| GET | `/api/cameras/<id>/detections` | Current detection counts |
| GET, POST | `/api/cameras/<id>/roi` | Read and save ROI zones |
| GET | `/api/logs`, `/api/logs/summary` | Vehicle logs and summary |

There are also admin-only endpoints for deleting cameras, deleting logs, and resetting the counter.

## Usage notes

- A camera can have only one `/feed` stream at a time. After changing the ROI or the video source, reopen the Dashboard.
- ROI zones must not overlap (the first matching zone wins).
- The first `/feed` request after a restart is slow because YOLO runs on the CPU.
- The backend uses UTC; the frontend displays WIB.

## Known limitations

- HTTP only, no HTTPS yet
- `/feed` can be accessed without login (it is loaded through an `<img>` tag)
- A single gunicorn worker and CPU-only inference, so capacity is limited
- No scheduled database backups and no automatic reconnect for `LIVE_CCTV` yet
- Memory grows slowly on long-running streams (`seen_ids` is never cleaned up)
- Accuracy is weaker for motorcycles and for car/truck classification (root cause: training data)
- The History page loads only the latest 5,000 logs

## Security

- Never commit `.env`, passwords, or tokens. Use strong, unique passwords for the database and the admin account, and change the default password after installation.
- Restrict PostgreSQL to `localhost` and use a firewall to close ports you do not need.

## Team

Add the team members' names here.
