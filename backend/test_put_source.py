import requests

url = "http://127.0.0.1:5000/api/cameras/cam_test/source"

data = {
    "rtsp_url": "rtsp://192.168.1.100:554/stream",
    "default_video_path": "videos/camera_test.mp4"
}

response = requests.put(url, json=data)

print("Status:", response.status_code)
print("Response:")
print(response.json())