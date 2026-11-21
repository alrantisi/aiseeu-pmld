from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import cv2
import base64
import threading
import json
from vehicle_detection.vehicle_detector import VehicleDetector
import os
import sys

app = Flask(__name__, 
            template_folder='../Frontend',
            static_folder='../Frontend/static')
CORS(app)

# Global detector instance
detector = None
processing_thread = None

def init_detector():
    """Initialize vehicle detector"""
    global detector
    try:
        detector = VehicleDetector()
        print("Vehicle Detector initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing detector: {e}")
        return False

def generate_frames():
    """Generate frames untuk video streaming"""
    while True:
        frame, vehicle_counts = detector.get_latest_frame()
        
        if frame is None:
            continue
        
        # Encode frame ke JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Yield frame dalam MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' 
               + frame_bytes + b'\r\n')

# API Routes

@app.route('/')
def index():
    """Render dashboard"""
    return render_template('dashboard.html')

@app.route('/api/video/stream')
def video_stream():
    """Video streaming endpoint"""
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/vehicle/counts', methods=['GET'])
def get_vehicle_counts():
    """Get current vehicle counts"""
    if detector is None:
        return jsonify({"error": "Detector not initialized"}), 500
    
    counts = detector.get_vehicle_counts()
    return jsonify({
        "status": "success",
        "data": counts,
        "frame": detector.frame_count
    })

@app.route('/api/vehicle/counts-detailed', methods=['GET'])
def get_vehicle_counts_detailed():
    """Get detailed vehicle counts dengan total"""
    if detector is None:
        return jsonify({"error": "Detector not initialized"}), 500
    
    counts = detector.get_vehicle_counts()
    detailed = {}
    
    for intersection, vehicles in counts.items():
        total = sum(vehicles.values())
        detailed[intersection] = {
            "car": vehicles.get("car", 0),
            "motorcycle": vehicles.get("motorcycle", 0),
            "bus": vehicles.get("bus", 0),
            "truck": vehicles.get("truck", 0),
            "total": total
        }
    
    return jsonify({
        "status": "success",
        "data": detailed,
        "frame": detector.frame_count
    })

@app.route('/api/start-processing', methods=['POST'])
def start_processing():
    """Start video processing"""
    global detector, processing_thread
    
    data = request.json
    video_source = data.get('video_source', 0)  # Default ke camera 0
    output_path = data.get('output_path', None)
    
    # Validate video source
    if isinstance(video_source, str):
        if not (video_source.startswith('rtsp://') or video_source.startswith('http') or os.path.exists(video_source)):
            return jsonify({"error": "Invalid video source"}), 400
    
    try:
        if detector is None:
            if not init_detector():
                return jsonify({"error": "Failed to initialize detector"}), 500
        
        # Stop existing processing
        if processing_thread and processing_thread.is_alive():
            detector.stop()
            processing_thread.join(timeout=5)
        
        # Start new processing thread
        processing_thread = detector.start_processing_thread(video_source, output_path)
        
        return jsonify({
            "status": "success",
            "message": f"Started processing from {video_source}"
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/stop-processing', methods=['POST'])
def stop_processing():
    """Stop video processing"""
    global detector
    
    if detector:
        detector.stop()
    
    return jsonify({
        "status": "success",
        "message": "Processing stopped"
    })

@app.route('/api/reset-counts', methods=['POST'])
def reset_counts():
    """Reset vehicle counts"""
    if detector is None:
        return jsonify({"error": "Detector not initialized"}), 500
    
    data = request.json
    intersection = data.get('intersection', None)
    
    detector.reset_counts(intersection)
    
    return jsonify({
        "status": "success",
        "message": f"Counts reset for {intersection or 'all intersections'}"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    detector_status = "running" if detector and detector.is_running else "idle"
    
    return jsonify({
        "status": "success",
        "detector": detector_status,
        "frame_count": detector.frame_count if detector else 0
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get system configuration"""
    from vehicle_detection.config.config import VEHICLE_CLASSES, DETECTION_LINES
    
    return jsonify({
        "status": "success",
        "vehicle_classes": list(VEHICLE_CLASSES.values()),
        "intersections": list(DETECTION_LINES.keys())
    })

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Initialize detector
    init_detector()
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
