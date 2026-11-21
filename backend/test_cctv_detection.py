
import cv2
from ultralytics import YOLO

# URL CCTV Pingit 4
cctv_url = "https://cctvjss.jogjakota.go.id/atcs/ATCS_Lampu_Merah_Pingit4.stream/chunklist_w1976773459.m3u8"

# Memuat model YOLOv8
model = YOLO("yolov8n.pt")

# Membuka stream CCTV
cap = cv2.VideoCapture(cctv_url, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Gagal membuka stream CCTV!")
    exit()

vehicle_classes = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

print("Deteksi kendaraan dimulai...")
print("Tekan ESC untuk keluar.")

try:
    while True:
        success, frame = cap.read()

        if not success or frame is None:
            print("Gagal membaca frame CCTV.")
            break

        # Deteksi kendaraan
        results = model(frame, verbose=False)

        vehicle_count = 0

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id not in vehicle_classes:
                    continue

                vehicle_count += 1

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])

                label = (
                    f"{vehicle_classes[class_id]} "
                    f"{confidence:.2f}"
                )

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

        cv2.imshow("CCTV Vehicle Detection", frame)

        # ESC untuk keluar
        if cv2.waitKey(1) & 0xFF == 27:
            print("Deteksi dihentikan.")
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Stream CCTV ditutup.")
