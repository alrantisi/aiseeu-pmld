
import cv2

from flask import Blueprint, request, Response, current_app

from app.extensions import db
from app.models import CameraSource, ROIConfiguration
from app.services.video_service import (
    annotate_frame,
    get_video_capture,
    read_frame_loop
)
from ml_engine.vehicle_detector import get_detection_state


camera_bp = Blueprint(
    "camera",
    __name__,
    url_prefix="/api/cameras"
)


# =========================================================
# GET ALL CAMERAS
# =========================================================
@camera_bp.get("")
def get_cameras():
    cameras = CameraSource.query.all()

    result = []

    for camera in cameras:
        result.append({
            "id": camera.id,
            "camera_id": camera.camera_id,
            "rtsp_url": camera.rtsp_url,
            "default_video_path": camera.default_video_path,
            "current_source": camera.current_source,
            "last_checked_at": camera.last_checked_at,
            "last_online_at": camera.last_online_at
        })

    return {
        "status": "success",
        "data": result
    }, 200


# =========================================================
# CREATE CAMERA
# =========================================================
@camera_bp.post("")
def create_camera():
    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "Request body tidak ditemukan"
        }, 400

    camera_id = data.get("camera_id")
    rtsp_url = data.get("rtsp_url")
    default_video_path = data.get("default_video_path")

    if not camera_id or not default_video_path:
        return {
            "status": "error",
            "message": "camera_id dan default_video_path wajib diisi"
        }, 400

    existing_camera = CameraSource.query.filter_by(
        camera_id=camera_id
    ).first()

    if existing_camera:
        return {
            "status": "error",
            "message": "camera_id sudah terdaftar"
        }, 409

    camera = CameraSource(
        camera_id=camera_id,
        rtsp_url=rtsp_url,
        default_video_path=default_video_path,
        current_source="DEFAULT_LOOP"
    )

    try:
        db.session.add(camera)
        db.session.commit()

    except Exception as e:
        db.session.rollback()

        return {
            "status": "error",
            "message": "Gagal menambahkan kamera",
            "detail": str(e)
        }, 500

    return {
        "status": "success",
        "message": "Camera berhasil ditambahkan",
        "data": {
            "id": camera.id,
            "camera_id": camera.camera_id,
            "current_source": camera.current_source
        }
    }, 201


# =========================================================
# UPDATE CAMERA SOURCE
# =========================================================
@camera_bp.put("/<camera_id>/source")
def update_camera_source(camera_id):
    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "Request body tidak ditemukan"
        }, 400

    camera = CameraSource.query.filter_by(
        camera_id=camera_id
    ).first()

    if not camera:
        return {
            "status": "error",
            "message": "Camera tidak ditemukan"
        }, 404

    rtsp_url = data.get("rtsp_url")
    default_video_path = data.get("default_video_path")
    current_source = data.get("current_source")

    allowed_sources = [
        "DEFAULT_LOOP",
        "LIVE_CCTV"
    ]

    # Validasi sumber video
    if current_source is not None:
        if current_source not in allowed_sources:
            return {
                "status": "error",
                "message": "Pilihan sumber video tidak valid"
            }, 400

    # Perbarui URL CCTV
    if rtsp_url is not None:
        camera.rtsp_url = rtsp_url

    # Perbarui lokasi video default
    if default_video_path is not None:
        camera.default_video_path = default_video_path

    # Perbarui sumber video aktif
    if current_source is not None:

        if current_source == "LIVE_CCTV":
            if not camera.rtsp_url:
                return {
                    "status": "error",
                    "message": "URL CCTV belum tersedia"
                }, 400

        elif current_source == "DEFAULT_LOOP":
            if not camera.default_video_path:
                return {
                    "status": "error",
                    "message": "Video default belum tersedia"
                }, 400

        camera.current_source = current_source

    try:
        db.session.commit()

    except Exception as e:
        db.session.rollback()

        return {
            "status": "error",
            "message": "Gagal memperbarui camera source",
            "detail": str(e)
        }, 500

    return {
        "status": "success",
        "message": "Camera source berhasil diperbarui",
        "data": {
            "camera_id": camera.camera_id,
            "rtsp_url": camera.rtsp_url,
            "default_video_path": camera.default_video_path,
            "current_source": camera.current_source
        }
    }, 200


# =========================================================
# GET CAMERA SNAPSHOT
# =========================================================
@camera_bp.get("/<camera_id>/snapshot")
def get_snapshot(camera_id):
    camera = CameraSource.query.filter_by(
        camera_id=camera_id
    ).first()

    if not camera:
        return {
            "status": "error",
            "message": "Camera tidak ditemukan"
        }, 404

    cap, source_type = get_video_capture(camera)

    if cap is None:
        return {
            "status": "error",
            "message": "Tidak dapat membuka sumber video"
        }, 500

    try:
        success, frame = cap.read()

    finally:
        cap.release()

    if not success or frame is None or frame.size == 0:
        return {
            "status": "error",
            "message": "Gagal mengambil frame"
        }, 500

    success, encoded_image = cv2.imencode(
        ".jpg",
        frame
    )

    if not success:
        return {
            "status": "error",
            "message": "Gagal mengubah frame menjadi JPEG"
        }, 500

    return Response(
        encoded_image.tobytes(),
        mimetype="image/jpeg",
        headers={
            "X-Source-Type": source_type
        }
    )


# =========================================================
# GET LIVE VIDEO FEED
# =========================================================

@camera_bp.get("/<camera_id>/feed")
def get_live_feed(camera_id):
    camera = CameraSource.query.filter_by(
        camera_id=camera_id
    ).first()

    if not camera:
        return {
            "status": "error",
            "message": "Camera tidak ditemukan"
        }, 404

    roi_config = ROIConfiguration.query.filter_by(
        camera_id=camera_id
    ).first()

    roi_zones = roi_config.roi_zones if roi_config else []

    # Simpan objek Flask app agar bisa digunakan di generator.
    app = current_app._get_current_object()

    def generate():
        cap = None

        try:
            cap, source_type = get_video_capture(camera)

            if cap is None:
                print(
                    f"[{camera_id}] Gagal membuka sumber video"
                )
                return

            print(
                f"[{camera_id}] Streaming dimulai: {source_type}"
            )

            target_size = None
            while True:
                if source_type == "DEFAULT_LOOP":
                    success, frame = read_frame_loop(cap)
                else:
                    success, frame = cap.read()

                if not success or frame is None:
                    print(
                        f"[{camera_id}] Gagal membaca frame"
                    )
                    break

                if frame.size == 0:
                    continue
                if source_type != "DEFAULT_LOOP":
                    # Stream live bisa ganti resolusi; samakan ukuran supaya tracker tidak error
                    frame_size = (frame.shape[1], frame.shape[0])
                    if target_size is None:
                        target_size = frame_size
                    elif frame_size != target_size:
                        frame = cv2.resize(frame, target_size)

                original_frame = frame.copy()

                try:
                    processed_frame = annotate_frame(
                        frame.copy(),
                        camera_id,
                        roi_zones,
                        source_type,
                        app,
                    )

                    if (
                        processed_frame is None
                        or not hasattr(processed_frame, "size")
                        or processed_frame.size == 0
                    ):
                        processed_frame = original_frame

                except Exception as error:
                    print(
                        f"[{camera_id}] Error proses deteksi: {error}"
                    )
                    processed_frame = original_frame

                try:
                    success, buffer = cv2.imencode(
                        ".jpg",
                        processed_frame
                    )

                    if not success:
                        print(
                            f"[{camera_id}] Gagal encode frame"
                        )
                        continue

                except cv2.error as error:
                    print(
                        f"[{camera_id}] Error OpenCV: {error}"
                    )
                    continue

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buffer.tobytes()
                    + b"\r\n"
                )

        except GeneratorExit:
            print(
                f"[{camera_id}] Streaming dihentikan oleh client"
            )

        except Exception as error:
            print(
                f"[{camera_id}] Error streaming: {error}"
            )

        finally:
            if cap is not None:
                cap.release()

            print(
                f"[{camera_id}] Streaming selesai"
            )

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

# =========================================================
# GET VEHICLE DETECTIONS
# =========================================================
@camera_bp.get("/<camera_id>/detections")
def get_detections(camera_id):
    camera = CameraSource.query.filter_by(
        camera_id=camera_id
    ).first()

    if not camera:
        return {
            "status": "error",
            "message": "Camera tidak ditemukan"
        }, 404

    return {
        "status": "success",
        "data": get_detection_state(camera_id)
    }, 200
