
import cv2
import numpy as np
import supervision as sv

from ultralytics import YOLO
from trackers import ByteTrackTracker


# ==========================================
# 1. KONFIGURASI
# ==========================================

CCTV_URL = (
    "https://cctvjss.jogjakota.go.id/atcs/"
    "ATCS_Lampu_Merah_Pingit4.stream/"
    "chunklist_w1976773459.m3u8"
)

MODEL_PATH = "yolov8n.pt"

# Class kendaraan pada dataset COCO
VEHICLE_CLASSES = {
    2: "MOB",
    3: "MTR",
    5: "BUS",
    7: "TRK"
}

CONFIDENCE_THRESHOLD = 0.15

# ==========================================
# ROI SEMENTARA (HASIL GET POSTMAN)
# ==========================================

ROI_ZONES = [
    {
        "zone_id": "z1",
        "zone_name": "Utara",
        "points": [
            [0.10, 0.12],
            [0.45, 0.15],
            [0.50, 0.65],
            [0.08, 0.60]
        ]
    },
    {
        "zone_id": "z2",
        "zone_name": "Selatan",
        "points": [
            [0.55, 0.15],
            [0.90, 0.12],
            [0.92, 0.60],
            [0.58, 0.65]
        ]
    }
]

# ==========================================
# 2. LOAD MODEL DAN TRACKER
# ==========================================

print("Memuat model YOLOv8...")

model = YOLO(MODEL_PATH)

print("Menginisialisasi ByteTrack...")

tracker = ByteTrackTracker(
    track_activation_threshold=0.25,
    minimum_consecutive_frames=1
)

print("Model dan tracker berhasil disiapkan.")

# ==========================================
# KONVERSI ROI NORMALISASI KE PIXEL
# ==========================================

def convert_roi_to_pixels(roi_zones, frame_width, frame_height):
    converted_zones = []

    for zone in roi_zones:
        pixel_points = []

        for x, y in zone["points"]:
            x_pixel = round(x * (frame_width - 1))
            y_pixel = round(y * (frame_height - 1))

            pixel_points.append([x_pixel, y_pixel])

        converted_zones.append({
            "zone_id": zone["zone_id"],
            "zone_name": zone["zone_name"],
            "points": np.array(pixel_points, dtype=np.int32)
        })

    return converted_zones

# ==========================================
# 3. MEMBUKA CCTV
# ==========================================

print("Menghubungkan ke CCTV...")

cap = cv2.VideoCapture(CCTV_URL, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Gagal membuka CCTV!")
    raise SystemExit(1)

print("CCTV berhasil terhubung.")
print("Tekan ESC pada jendela video untuk keluar.")


# ==========================================
# 4. ANNOTATOR
# ==========================================

box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()


# ==========================================
# 5. PROSES DETEKSI DAN TRACKING
# ==========================================

try:
    while True:

        # Membaca frame CCTV
        success, frame = cap.read()

        if not success or frame is None:
            print("Frame CCTV gagal dibaca.")
            break

        # ----------------------------------
        # YOLO DETECTION
        # ----------------------------------
        results = model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            imgsz=1280,
            classes=[2, 3, 5, 7],
            verbose=False
        )[0]

        # Konversi hasil YOLO ke Supervision
        detections = sv.Detections.from_ultralytics(results)

        # ----------------------------------
        # BYTE TRACKING
        # ----------------------------------

        detections = tracker.update(detections)

        # ----------------------------------
        # LABEL KENDARAAN
        # ----------------------------------

        labels = []

        for class_id, confidence, track_id in zip(
            detections.class_id,
            detections.confidence,
            detections.tracker_id
        ):

            vehicle_name = VEHICLE_CLASSES[int(class_id)]

            labels.append(
                f"ID: {int(track_id)} | "
                f"{vehicle_name} | "
                f"{float(confidence):.2f}"
            )

        # ----------------------------------
        # VISUALISASI
        # ----------------------------------

        annotated_frame = box_annotator.annotate(
            scene=frame.copy(),
            detections=detections
        )

        annotated_frame = label_annotator.annotate(
            scene=annotated_frame,
            detections=detections,
            labels=labels
        )
        
        # ----------------------------------
        # ROI VISUALIZATION
        # ----------------------------------

        frame_height, frame_width = frame.shape[:2]

        pixel_roi_zones = convert_roi_to_pixels(
            ROI_ZONES,
            frame_width,
            frame_height
        )

        for zone in pixel_roi_zones:

            points = zone["points"]

            # Menggambar polygon ROI
            cv2.polylines(
                annotated_frame,
                [points],
                isClosed=True,
                color=(0, 255, 255),
                thickness=3
            )

            # Menampilkan nama zona
            label_x, label_y = points[0]

            cv2.putText(
                annotated_frame,
                zone["zone_name"],
                (label_x, max(label_y - 10, 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

        # Jumlah kendaraan yang sedang terlacak
        tracked_count = len(detections)

        cv2.putText(
            annotated_frame,
            f"Tracked Vehicles: {tracked_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        # Menampilkan video
        cv2.imshow(
            "YOLOv8 + ByteTrack - CCTV",
            annotated_frame
        )

        # ----------------------------------
        # ESC UNTUK KELUAR
        # ----------------------------------

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            print("Program dihentikan oleh pengguna.")
            break


# ==========================================
# 6. MEMBERSIHKAN RESOURCE
# ==========================================

except KeyboardInterrupt:
    print("Program dihentikan melalui keyboard.")

except Exception as error:
    print(f"Terjadi kesalahan: {error}")

finally:
    cap.release()
    cv2.destroyAllWindows()

    print("Koneksi CCTV ditutup.")
    print("Program selesai.")
