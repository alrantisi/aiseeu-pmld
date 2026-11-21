from app import create_app
from app.models import CameraSource
from app.services.video_service import get_video_capture

app = create_app()

with app.app_context():

    camera = CameraSource.query.filter_by(
        camera_id="cam_test"
    ).first()

    if not camera:
        print("Camera tidak ditemukan!")
    else:
        cap, source_type = get_video_capture(camera)

        print("Source type:", source_type)

        if cap is not None:
            print("Video berhasil dibuka!")

            success, frame = cap.read()

            print("Frame berhasil dibaca:", success)

            if frame is not None:
                print("Ukuran frame:", frame.shape)

            cap.release()

        else:
            print("Video gagal dibuka!")