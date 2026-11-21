import time
from datetime import datetime

from app import create_app
from app.extensions import db
from app.models import CameraSource
from app.services.video_service import get_video_capture, read_frame_loop


def run_video_manager(camera_id):
    app = create_app()

    with app.app_context():

        camera = CameraSource.query.filter_by(
            camera_id=camera_id
        ).first()

        if not camera:
            print(f"Camera {camera_id} tidak ditemukan.")
            return

        print(f"Video Manager aktif untuk {camera_id}")

        while True:

            print("Mengecek sumber video...")

            cap, source_type = get_video_capture(camera)

            now = datetime.now()

            camera.current_source = source_type
            camera.last_checked_at = now

            if source_type == "LIVE_CCTV":
                camera.last_online_at = now

            db.session.commit()

            print(f"Source: {source_type}")

            if cap is None:
                print("Tidak ada sumber video yang tersedia.")
                time.sleep(15)
                continue

            if source_type == "DEFAULT_LOOP":
                success, frame = read_frame_loop(cap)
            else:
                success, frame = cap.read()

            if success and frame is not None:
                print("Frame berhasil diterima.")
            else:
                print("Frame gagal dibaca.")

            cap.release()


if __name__ == "__main__":
    run_video_manager("cam_test")