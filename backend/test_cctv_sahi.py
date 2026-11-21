
import cv2
import time
import torch

from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction


# ==========================================
# 1. KONFIGURASI
# ==========================================

CCTV_URL = (
    "https://cctvjss.jogjakota.go.id/atcs/"
    "ATCS_Lampu_Merah_Pingit4.stream/"
    "chunklist_w1976773459.m3u8"
)

MODEL_PATH = "yolov8n.pt"

CONFIDENCE = 0.25

# Ukuran potongan gambar
SLICE_HEIGHT = 512
SLICE_WIDTH = 512

# Overlap antar potongan
OVERLAP = 0.20

VEHICLE_CLASSES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}


# ==========================================
# 2. DEVICE
# ==========================================

device = "cuda:0" if torch.cuda.is_available() else "cpu"

print("Device:", device)


# ==========================================
# 3. LOAD YOLOv8s MELALUI SAHI
# ==========================================

print("Memuat YOLOv8s...")

detection_model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path=MODEL_PATH,
    confidence_threshold=CONFIDENCE,
    device=device
)

print("Model berhasil dimuat.")


# ==========================================
# 4. MEMBUKA CCTV
# ==========================================

print("Menghubungkan ke CCTV...")

cap = cv2.VideoCapture(CCTV_URL, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Gagal membuka CCTV!")
    raise SystemExit(1)

print("CCTV berhasil dibuka.")
print("Tekan ESC untuk keluar.")


# ==========================================
# 5. DETEKSI SAHI
# ==========================================

frame_number = 0
start_time = time.time()

try:
    while True:

        success, frame = cap.read()

        if not success or frame is None:
            print("Gagal membaca frame CCTV.")
            break

        frame_number += 1

        # SAHI sliced inference
        result = get_sliced_prediction(
            image=frame,
            detection_model=detection_model,
            slice_height=SLICE_HEIGHT,
            slice_width=SLICE_WIDTH,
            overlap_height_ratio=OVERLAP,
            overlap_width_ratio=OVERLAP,
            postprocess_type="GREEDYNMM",
            postprocess_match_metric="IOS",
            postprocess_match_threshold=0.5,
            verbose=0
        )

        annotated_frame = frame.copy()
        vehicle_count = 0

        # Menggambar hasil deteksi
        for prediction in result.object_prediction_list:

            try:
                class_id = int(prediction.category.id)
            except (ValueError, TypeError):
                continue

            if class_id not in VEHICLE_CLASSES:
                continue

            vehicle_count += 1

            x1, y1, x2, y2 = map(
                int, prediction.bbox.to_xyxy()
            )

            confidence = prediction.score.value
            label = (
                f"{VEHICLE_CLASSES[class_id]} "
                f"{confidence:.2f}"
            )

            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                annotated_frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        # Hitung FPS rata-rata
        elapsed = time.time() - start_time
        fps = frame_number / elapsed if elapsed > 0 else 0

        cv2.putText(
            annotated_frame,
            f"Vehicles: {vehicle_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"FPS: {fps:.2f}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )

        cv2.imshow(
            "YOLOv8s + SAHI - CCTV",
            annotated_frame
        )

        if cv2.waitKey(1) & 0xFF == 27:
            print("Pengujian dihentikan.")
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("CCTV ditutup.")
