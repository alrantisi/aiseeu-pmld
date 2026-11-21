
import cv2
from ultralytics import YOLO

# Memuat model YOLOv8 Nano
model = YOLO("yolov8n.pt")

# Membuka video lokal
video_path = "videos/camera_test.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Gagal membuka video!")
    exit()

# Class kendaraan pada dataset COCO
vehicle_classes = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

print("Memulai deteksi kendaraan...")

while True:
    success, frame = cap.read()

    if not success:
        break

    # Deteksi objek menggunakan YOLO
    results = model(frame, verbose=False)

    vehicle_count = 0

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])

            # Hanya mengambil objek kendaraan
            if class_id not in vehicle_classes:
                continue

            vehicle_count += 1

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])

            label = (
                f"{vehicle_classes[class_id]} "
                f"{confidence:.2f}"
            )

            # Menggambar bounding box
            cv2.rectangle(
                frame, (x1, y1), (x2, y2),
                (0, 255, 0), 2
            )

            cv2.putText(
                frame, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 255, 0), 2
            )

    cv2.putText(
        frame,
        f"Vehicle detected: {vehicle_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1, (0, 0, 255), 2
    )

    cv2.imshow("YOLOv8 Vehicle Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("Pengujian selesai.")
