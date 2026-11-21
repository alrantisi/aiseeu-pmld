import cv2

video_path = "videos/camera_test.mp4"

cap = cv2.VideoCapture(video_path)

print("Video terbuka:", cap.isOpened())

success, frame = cap.read()

print("Frame berhasil dibaca:", success)

if frame is not None:
    print("Ukuran frame:", frame.shape)

cap.release()