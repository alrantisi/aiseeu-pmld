import requests
import streamlit as st

BASE_URL = "http://localhost:5000"
TIMEOUT = 10
SESSION_COOKIE = "session"


def get_session():
    """Satu requests.Session per sesi Streamlit, supaya cookie Flask kebawa."""
    if "api_session" not in st.session_state:
        st.session_state.api_session = requests.Session()
    return st.session_state.api_session


def _error_message(response, default):
    try:
        return response.json().get("message", default)
    except ValueError:
        return default


def login(username, password):
    """Return (True, user_dict) kalau sukses, (False, pesan_error) kalau gagal."""
    try:
        response = get_session().post(
            f"{BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return False, "Backend tidak bisa dihubungi"

    if response.status_code == 200:
        return True, response.json().get("user", {})
    return False, _error_message(response, "Login gagal")


def get_session_token():
    """Nilai cookie login dari backend (untuk disimpan di browser), atau None."""
    token = None
    for cookie in get_session().cookies:
        if cookie.name == SESSION_COOKIE:
            token = cookie.value
    return token


def restore_session(token):
    """Pulihkan login dari token yang tersimpan di cookie browser.
    Return (status, user_dict): status 'ok', 'invalid' (token ditolak),
    atau 'unreachable' (backend tidak bisa dihubungi)."""
    session = get_session()
    session.cookies.set(SESSION_COOKIE, token)
    try:
        response = session.get(f"{BASE_URL}/api/auth/check", timeout=TIMEOUT)
    except requests.RequestException:
        session.cookies.clear()
        return "unreachable", {}

    if response.status_code == 200:
        try:
            return "ok", response.json().get("user", {})
        except ValueError:
            pass
    session.cookies.clear()
    return "invalid", {}


def logout():
    """Logout di backend lalu buang session lokal (cookie ikut hilang)."""
    try:
        get_session().post(f"{BASE_URL}/api/auth/logout", timeout=TIMEOUT)
    except requests.RequestException:
        pass
    st.session_state.pop("api_session", None)


def get_cameras():
    """Return list kamera dari backend, atau list kosong kalau gagal."""
    try:
        response = get_session().get(f"{BASE_URL}/api/cameras", timeout=TIMEOUT)
        response.raise_for_status()
        return response.json().get("data", [])
    except (requests.RequestException, ValueError):
        return []


def update_camera_source(
    camera_id, rtsp_url=None, default_video_path=None, current_source=None
):
    """Ubah sumber video kamera. Field yang None tidak dikirim.
    Return (True, pesan) atau (False, pesan)."""
    candidates = {
        "rtsp_url": rtsp_url,
        "default_video_path": default_video_path,
        "current_source": current_source,
    }
    payload = {k: v for k, v in candidates.items() if v is not None}

    try:
        response = get_session().put(
            f"{BASE_URL}/api/cameras/{camera_id}/source",
            json=payload,
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return False, "Backend tidak bisa dihubungi"

    if response.status_code == 200:
        return True, "Sumber video berhasil diperbarui"
    return False, _error_message(response, "Gagal memperbarui sumber video")


def get_detections(camera_id):
    """Return dict hitungan deteksi dari backend, atau None kalau gagal."""
    try:
        response = get_session().get(
            f"{BASE_URL}/api/cameras/{camera_id}/detections",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("data")
    except (requests.RequestException, ValueError):
        return None


def get_roi(camera_id):
    """Return list zona ROI. List kosong kalau belum ada atau gagal."""
    try:
        response = get_session().get(
            f"{BASE_URL}/api/cameras/{camera_id}/roi",
            timeout=TIMEOUT,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json().get("data", {}).get("roi_zones", [])
    except (requests.RequestException, ValueError):
        return []


def save_roi(camera_id, roi_zones):
    """Simpan seluruh daftar zona. Return (True, pesan) atau (False, pesan)."""
    try:
        response = get_session().post(
            f"{BASE_URL}/api/cameras/{camera_id}/roi",
            json={"roi_zones": roi_zones},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return False, "Backend tidak bisa dihubungi"

    if response.status_code == 200:
        return True, "ROI berhasil disimpan"
    return False, _error_message(response, "Gagal menyimpan ROI")


def get_snapshot(camera_id):
    """Return bytes JPEG satu frame kamera, atau None kalau gagal."""
    try:
        response = get_session().get(
            f"{BASE_URL}/api/cameras/{camera_id}/snapshot",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None


def get_logs(camera_id=None, max_pages=50):
    """Ambil semua log (100 per halaman, maksimal max_pages halaman)."""
    logs = []
    page = 1
    while page <= max_pages:
        params = {"page": page, "per_page": 100}
        if camera_id:
            params["camera_id"] = camera_id
        try:
            response = get_session().get(
                f"{BASE_URL}/api/logs", params=params, timeout=TIMEOUT
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            break
        logs.extend(body.get("data", []))
        if page >= body.get("pagination", {}).get("total_pages", 0):
            break
        page += 1
    return logs


def get_logs_summary(camera_id=None):
    """Return dict rekap log, atau None kalau gagal."""
    params = {"camera_id": camera_id} if camera_id else {}
    try:
        response = get_session().get(
            f"{BASE_URL}/api/logs/summary", params=params, timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("data")
    except (requests.RequestException, ValueError):
        return None


def create_camera(camera_id, rtsp_url, default_video_path):
    """Tambah kamera baru. Return (True, pesan) atau (False, pesan)."""
    try:
        response = get_session().post(
            f"{BASE_URL}/api/cameras",
            json={
                "camera_id": camera_id,
                "rtsp_url": rtsp_url,
                "default_video_path": default_video_path,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return False, "Backend tidak bisa dihubungi"

    if response.status_code in (200, 201):
        return True, "Kamera berhasil ditambahkan"
    return False, _error_message(response, "Gagal menambah kamera")


def delete_logs(camera_id, ids):
    """Hapus log berdasarkan daftar ID. Return (True, pesan) atau (False, pesan)."""
    try:
        response = get_session().delete(
            f"{BASE_URL}/api/logs",
            params={"camera_id": camera_id},
            json={"ids": ids},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return False, "Backend tidak bisa dihubungi"

    if response.status_code == 200:
        try:
            deleted = response.json().get("data", {}).get("deleted", 0)
        except ValueError:
            deleted = 0
        return True, f"{deleted} event log kamera {camera_id} dihapus."
    return False, _error_message(response, "Gagal menghapus log")
