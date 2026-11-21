import cv2

from app.services.video_service import open_default_video, read_frame_loop


video_path = "videos/camera_test.mp4"

cap = open_default_video(video_path)

if cap is None:
    print("Video gagal dibuka!")
    exit()

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print("Total frame:", total_frames)

# Lompat ke frame terakhir
cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)

print("Posisi sebelum looping:",
      int(cap.get(cv2.CAP_PROP_POS_FRAMES)))

# Baca frame terakhir
success, frame = read_frame_loop(cap)

print("Baca frame terakhir:", success)
print("Posisi setelah baca:",
      int(cap.get(cv2.CAP_PROP_POS_FRAMES)))

# Panggil lagi untuk menguji apakah kembali ke awal
success, frame = read_frame_loop(cap)

print("Baca setelah looping:", success)
print("Posisi setelah looping:",
      int(cap.get(cv2.CAP_PROP_POS_FRAMES)))

cap.release()