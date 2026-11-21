import cv2

from ml_engine.vehicle_detector import annotate_frame


def open_live_stream(url):
    """
    Membuka live stream CCTV dan memastikan frame pertama
    berhasil dibaca.
    """

    if not url:
        return None

    cap = cv2.VideoCapture(
        url,
        cv2.CAP_FFMPEG
    )

    cap.set(
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
        3000
    )

    cap.set(
        cv2.CAP_PROP_READ_TIMEOUT_MSEC,
        3000
    )

    if not cap.isOpened():
        cap.release()
        return None

    success, frame = cap.read()

    if success and frame is not None:
        return cap

    cap.release()
    return None


def open_default_video(path):
    """
    Membuka video default.
    """

    if not path:
        return None

    cap = cv2.VideoCapture(path)

    if cap.isOpened():
        return cap

    cap.release()
    return None


def get_video_capture(camera):
    """
    Membuka sumber video berdasarkan current_source
    yang dipilih pada database.

    Pilihan sumber:
    1. LIVE_CCTV
    2. DEFAULT_LOOP

    Tidak melakukan fallback otomatis ke sumber lain.
    """

    current_source = camera.current_source

    # Jika pengguna memilih LIVE_CCTV
    if current_source == "LIVE_CCTV":

        cap = open_live_stream(camera.rtsp_url)

        if cap is not None:
            print(f"[{camera.camera_id}] Sumber video: LIVE_CCTV")
            return cap, "LIVE_CCTV"

        print(f"[{camera.camera_id}] Gagal membuka LIVE_CCTV")

        return None, None

    # Jika pengguna memilih DEFAULT_LOOP
    elif current_source == "DEFAULT_LOOP":

        cap = open_default_video(camera.default_video_path)

        if cap is not None:
            print(f"[{camera.camera_id}] Sumber video: DEFAULT_LOOP")
            return cap, "DEFAULT_LOOP"

        print(f"[{camera.camera_id}] Gagal membuka DEFAULT_LOOP")

        return None, None

    # Jika sumber tidak dikenali
    print(
        f"[{camera.camera_id}] "
        f"Sumber video tidak valid: {current_source}"
    )

    return None, None


def read_frame_loop(cap):
    """
    Membaca satu frame dari video default.
    Jika video sudah mencapai akhir, kembali ke frame pertama.
    """

    success, frame = cap.read()

    if success and frame is not None:
        return True, frame

    # Video sudah mencapai akhir, ulang dari awal
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    success, frame = cap.read()

    if success and frame is not None:
        return True, frame

    return False, None