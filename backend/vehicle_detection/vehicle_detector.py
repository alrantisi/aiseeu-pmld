import cv2
import numpy as np
from ultralytics import YOLO
from vehicle_detection.centroid_tracker import CentroidTracker
from vehicle_detection.config.config import (
    MODEL_PATH, CONFIDENCE_THRESHOLD, VEHICLE_CLASSES, COLORS, 
    DETECTION_LINES, MAX_DISTANCE_THRESHOLD
)
import threading
import queue

class VehicleDetector:
    """
    Main class untuk deteksi dan tracking kendaraan dari video atau stream
    """
    def __init__(self):
        self.model = YOLO(MODEL_PATH)
        self.trackers = {}  # Per intersection tracker
        self.frame_count = 0
        self.vehicle_counts = {}
        self.is_running = False
        self.frame_queue = queue.Queue(maxsize=10)
        
        # Initialize trackers untuk setiap intersection
        for intersection_name in DETECTION_LINES.keys():
            self.trackers[intersection_name] = CentroidTracker()
            self.vehicle_counts[intersection_name] = {}

    def detect_and_track(self, frame):
        """
        Deteksi dan track kendaraan dalam frame
        
        Args:
            frame: input frame dari video/camera
            
        Returns:
            annotated_frame: frame dengan bounding boxes dan info
            vehicle_counts: dictionary dengan count per jenis kendaraan per intersection
        """
        self.frame_count += 1
        results = self.model(frame)
        
        # Extract detections
        detections = []
        vehicle_classes_list = []
        
        if results and len(results) > 0:
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        conf = float(box.conf)
                        if conf < CONFIDENCE_THRESHOLD:
                            continue
                        
                        cls = int(box.cls)
                        
                        # Filter hanya vehicle classes
                        if cls not in VEHICLE_CLASSES:
                            continue
                        
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        detections.append((x1, y1, x2, y2))
                        vehicle_classes_list.append(VEHICLE_CLASSES[cls])

        # Update trackers untuk setiap intersection
        annotated_frame = frame.copy()
        
        for intersection_name, tracker in self.trackers.items():
            # Update tracker dengan detections
            objects, vehicle_counts = tracker.update(detections, vehicle_classes_list)
            
            # Get detection line untuk intersection ini
            line_config = DETECTION_LINES[intersection_name]
            line_start = line_config["line_start"]
            line_end = line_config["line_end"]
            
            # Check line crossing
            tracker.check_line_crossing(line_start, line_end)
            
            # Update counts
            self.vehicle_counts[intersection_name] = tracker.get_vehicle_count()
            
            # Draw detection line
            annotated_frame = self._draw_detection_line(
                annotated_frame, line_start, line_end, line_config["color"]
            )
        
        # Draw bounding boxes dan labels
        annotated_frame = self._draw_detections(annotated_frame, detections, vehicle_classes_list)
        
        # Draw vehicle counts
        annotated_frame = self._draw_vehicle_counts(annotated_frame)
        
        return annotated_frame, self.vehicle_counts

    def _draw_detections(self, frame, detections, vehicle_classes_list):
        """Draw bounding boxes dan labels pada frame"""
        for (x1, y1, x2, y2), vehicle_class in zip(detections, vehicle_classes_list):
            color = COLORS.get(vehicle_class, (0, 255, 0))
            
            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = vehicle_class.upper()
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Background untuk label
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 4), 
                         (x1 + label_size[0], y1), color, -1)
            
            # Text
            cv2.putText(frame, label, (x1, y1 - 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame

    def _draw_detection_line(self, frame, line_start, line_end, color):
        """Draw detection line pada frame"""
        cv2.line(frame, line_start, line_end, color, 2)
        
        # Draw circle di ujung line
        cv2.circle(frame, line_start, 5, color, -1)
        cv2.circle(frame, line_end, 5, color, -1)
        
        return frame

    def _draw_vehicle_counts(self, frame):
        """Draw vehicle counts pada frame"""
        height = frame.shape[0]
        y_offset = 30
        
        for intersection_name, counts in self.vehicle_counts.items():
            # Draw background panel
            cv2.rectangle(frame, (10, y_offset - 25), (400, y_offset + 120), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, y_offset - 25), (400, y_offset + 120), (255, 255, 255), 2)
            
            # Draw intersection name
            cv2.putText(frame, f"Intersection: {intersection_name}", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw vehicle counts
            vehicles_list = [
                ("CAR", "car"),
                ("MOTORCYCLE", "motorcycle"),
                ("BUS", "bus"),
                ("TRUCK", "truck")
            ]
            
            line_offset = y_offset + 25
            for label, class_name in vehicles_list:
                count = counts.get(class_name, 0)
                color = COLORS.get(class_name, (200, 200, 200))
                text = f"{label}: {count}"
                
                cv2.putText(frame, text, (20, line_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                line_offset += 25
            
            y_offset += 150

        # Draw frame count
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, height - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return frame

    def process_video(self, video_source, output_path=None):
        """
        Process video file atau stream
        
        Args:
            video_source: path ke video file, camera index, atau stream URL
            output_path: path untuk menyimpan output video (opsional)
        """
        cap = cv2.VideoCapture(video_source)
        
        if not cap.isOpened():
            raise ValueError(f"Tidak bisa membuka video source: {video_source}")
        
        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        
        # Setup output video writer jika diperlukan
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        self.is_running = True
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize frame untuk lebih cepat (optional)
            # frame = cv2.resize(frame, (960, 540))
            
            # Detect dan track
            annotated_frame, vehicle_counts = self.detect_and_track(frame)
            
            # Push ke queue untuk streaming
            try:
                self.frame_queue.put_nowait((annotated_frame, vehicle_counts))
            except queue.Full:
                pass  # Skip frame jika queue penuh
            
            # Write output video
            if out:
                out.write(annotated_frame)
            
            # Display (opsional, bisa di-comment untuk production)
            cv2.imshow('Vehicle Detection', annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.is_running = False
                break
        
        cap.release()
        if out:
            out.release()
        cv2.destroyAllWindows()

    def get_latest_frame(self):
        """Get frame terbaru dari queue"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None, None

    def start_processing_thread(self, video_source, output_path=None):
        """Start processing dalam thread terpisah"""
        thread = threading.Thread(
            target=self.process_video,
            args=(video_source, output_path),
            daemon=True
        )
        thread.start()
        return thread

    def stop(self):
        """Stop processing"""
        self.is_running = False

    def get_vehicle_counts(self):
        """Get current vehicle counts"""
        return self.vehicle_counts

    def reset_counts(self, intersection_name=None):
        """Reset vehicle counts"""
        if intersection_name:
            self.vehicle_counts[intersection_name] = {}
            if intersection_name in self.trackers:
                self.trackers[intersection_name].detected_vehicles.clear()
        else:
            for key in self.vehicle_counts:
                self.vehicle_counts[key] = {}
            for tracker in self.trackers.values():
                tracker.detected_vehicles.clear()
