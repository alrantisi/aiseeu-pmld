from app import create_app
from app.extensions import db
from app.models import (
    ROIConfiguration,
    CameraSource,
    VehicleLog
)


app = create_app()


with app.app_context():

    try:
        # =========================
        # 1. DATA CAMERA
        # =========================

        camera = CameraSource(
            camera_id="cam_test",
            rtsp_url="rtsp://192.168.1.100:554/stream",
            default_video_path="videos/camera_test.mp4",
            current_source="DEFAULT_LOOP"
        )

        db.session.add(camera)


        # =========================
        # 2. DATA ROI
        # =========================

        roi = ROIConfiguration(
            camera_id="cam_test",
            roi_zones=[
                {
                    "zone_id": "z1",
                    "zone_name": "Kendaraan Masuk",
                    "polygon": [
                        {"x": 100, "y": 200},
                        {"x": 300, "y": 200},
                        {"x": 300, "y": 500},
                        {"x": 100, "y": 500}
                    ]
                },
                {
                    "zone_id": "z2",
                    "zone_name": "Kendaraan Keluar",
                    "polygon": [
                        {"x": 500, "y": 100},
                        {"x": 800, "y": 100},
                        {"x": 800, "y": 400},
                        {"x": 500, "y": 400}
                    ]
                }
            ]
        )

        db.session.add(roi)


        # =========================
        # 3. DATA VEHICLE LOG
        # =========================

        vehicle = VehicleLog(
            camera_id="cam_test",
            zone_id="z1",
            zone_name="Kendaraan Masuk",
            track_id=101,
            vehicle_type="car",
            action="ENTER",
            confidence=0.95,
            source_type="DEFAULT_LOOP"
        )

        db.session.add(vehicle)


        # =========================
        # SIMPAN
        # =========================

        db.session.commit()

        print("================================")
        print("INSERT BERHASIL!")
        print("================================")


        # =========================
        # TEST SELECT
        # =========================

        cameras = CameraSource.query.all()
        rois = ROIConfiguration.query.all()
        vehicles = VehicleLog.query.all()


        print("\nCAMERA SOURCES:")
        for camera in cameras:
            print(
                camera.id,
                camera.camera_id,
                camera.current_source
            )


        print("\nROI CONFIGURATIONS:")
        for roi in rois:
            print(
                roi.id,
                roi.camera_id,
                roi.roi_zones
            )


        print("\nVEHICLE LOGS:")
        for vehicle in vehicles:
            print(
                vehicle.id,
                vehicle.camera_id,
                vehicle.zone_id,
                vehicle.vehicle_type,
                vehicle.action,
                vehicle.confidence,
                vehicle.source_type
            )


    except Exception as e:

        db.session.rollback()

        print("================================")
        print("TEST GAGAL!")
        print("================================")
        print(e)