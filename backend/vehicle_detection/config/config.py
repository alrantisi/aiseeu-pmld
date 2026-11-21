# Konfigurasi untuk Vehicle Detection System

# Model Configuration
MODEL_PATH = "yolov8n.pt"  # YOLOv8 nano model
CONFIDENCE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.4

# Vehicle Classes (sesuai COCO dataset)
VEHICLE_CLASSES = {
    2: "car",           # mobil
    3: "motorcycle",    # motor
    5: "bus",          # bus
    7: "truck"         # truk
}

# Tracking Configuration
MAX_DISTANCE_THRESHOLD = 50  # pixels
MAX_FRAMES_TO_SKIP = 30

# Detection Line Configuration (untuk menghitung kendaraan yang melewati)
DETECTION_LINES = {
    "intersection_1": {
        "line_start": (100, 300),
        "line_end": (800, 300),
        "color": (0, 255, 0)
    },
    "intersection_2": {
        "line_start": (100, 200),
        "line_end": (800, 200),
        "color": (255, 0, 0)
    }
}

# Colors for drawing
COLORS = {
    "car": (0, 255, 0),      # Green
    "motorcycle": (255, 0, 0),  # Blue
    "bus": (0, 0, 255),      # Red
    "truck": (255, 255, 0),  # Cyan
}

# Dashboard Configuration
DASHBOARD_UPDATE_INTERVAL = 1000  # ms
FPS_TARGET = 30

# Video Input Configuration
VIDEO_INPUT_TYPE = "video"  # "video", "camera", atau "stream"
VIDEO_PATH = "path/to/video.mp4"
CAMERA_ID = 0
STREAM_URL = "rtsp://camera_ip:port/stream"

# Output Configuration
ENABLE_OUTPUT_VIDEO = True
OUTPUT_VIDEO_PATH = "output_video.mp4"
