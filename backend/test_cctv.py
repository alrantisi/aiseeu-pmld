import cv2

url = "https://cctvjss.jogjakota.go.id/atcs/ATCS_Lampu_Merah_Pingit4.stream/chunklist_w1976773459.m3u8"

cap = cv2.VideoCapture(url)

print("Stream terbuka:", cap.isOpened())

success, frame = cap.read()

print("Frame berhasil dibaca:", success)

if frame is not None:
    print("Ukuran frame:", frame.shape)

cap.release()