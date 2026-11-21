import requests

url = "http://127.0.0.1:5000/api/cameras"

data = {
    "camera_id": "cam_01",
    "rtsp_url": "rtsp://192.168.1.100:554/stream",
    "default_video_path": "videos/camera_01.mp4"
}

response = requests.post(url, json=data)

print("Status:", response.status_code)
print("Response:")
print(response.json())