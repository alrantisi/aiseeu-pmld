
import os
import threading
from pathlib import Path
from typing import Any

import cv2

from app.extensions import db
from app.models import VehicleLog


class VehicleDetector:
    """Deteksi kendaraan, pencatatan aktivitas ROI, dan perpindahan zona."""

    CLASS_NAMES = {
        1: "Mobil",
        2: "Motor",
        0: "Bus",
        3: "Truk",
    }

    COLORS = {
        "Motor": (16, 185, 129),
        "Mobil": (6, 182, 212),
        "Bus": (245, 158, 11),
        "Truk": (168, 85, 247),
    }

    CLASS_KEYS = {
        "Mobil": "car",
        "Motor": "motorcycle",
        "Bus": "bus",
        "Truk": "truck",
    }

    # Toleransi ketika kendaraan tidak terdeteksi.
    OUTSIDE_ROI_TOLERANCE = 15
    LOST_TRACK_TOLERANCE = 30

    def __init__(self):
        self.model: Any = None
        self.load_attempted = False
        self.lock = threading.Lock()
        self.states = {}
        self.trackers_by_camera = {}
        self.frame_shapes = {}

        self.confidence = float(
            os.getenv("YOLO_CONFIDENCE", "0.10")
        )

        self.model_path = os.getenv(
            "YOLO_MODEL_PATH",
            "yolov8n.pt"
        )

        self.model_error = None

    def _load_model(self):
        if self.load_attempted:
            return

        self.load_attempted = True

        try:
            from ultralytics import YOLO

            model_path = Path(self.model_path)

            if not model_path.is_absolute() and not model_path.exists():
                model_path = (
                    Path(__file__).resolve().parents[1] / model_path
                )

            self.model = YOLO(str(model_path))

        except Exception as error:
            self.model_error = str(error)
            print(f"YOLO tidak aktif: {error}")
            self.model = None

    def _get_state(self, camera_id):
        if camera_id not in self.states:
            self.states[camera_id] = {
                "total": 0,
                "car": 0,
                "motorcycle": 0,
                "bus": 0,
                "truck": 0,
                "seen_ids": set(),
                "detections": [],
                "error": None,
                "zones": [],
                "zone_counts": {},
                "zone_seen_ids": {},
                "track_last_zones": {},
                "track_last_seen": {},
                "track_outside_frames": {},
                "frame_index": 0,
                "movement_counts": {},
                "movements": [],
            }

        return self.states[camera_id]

    def _sync_zones(self, state, zones):
        state["zones"] = [
            zone for zone in zones
            if isinstance(zone, dict)
            and isinstance(zone.get("points"), list)
            and len(zone["points"]) >= 3
        ]

        for zone in state["zones"]:
            zone_id = zone.get("zone_id")

            if not zone_id:
                continue

            state["zone_counts"].setdefault(
                zone_id,
                {"total": 0, "in": 0, "out": 0}
            )

            state["zone_seen_ids"].setdefault(
                zone_id,
                set()
            )

    @staticmethod
    def _get_zone_name(state, zone_id):
        for zone in state["zones"]:
            if zone.get("zone_id") == zone_id:
                return zone.get("zone_name", zone_id)

        return zone_id

    def _save_log(
        self,
        app,
        camera_id,
        zone_id,
        track_id,
        vehicle_type,
        action,
        confidence,
        source_type,
    ):
        """Simpan satu aktivitas kendaraan ke database."""

        try:
            with app.app_context():
                log = VehicleLog(
                    camera_id=camera_id,
                    zone_id=zone_id,
                    zone_name=self._get_zone_name(
                        self._get_state(camera_id),
                        zone_id
                    ),
                    track_id=track_id,
                    vehicle_type=vehicle_type,
                    action=action,
                    confidence=confidence,
                    source_type=source_type,
                )

                db.session.add(log)
                db.session.commit()

        except Exception as error:
            with app.app_context():
                db.session.rollback()

            print(
                f"[{camera_id}] Gagal menyimpan log "
                f"{action} zona {zone_id}: {error}"
            )

    def _record_event(
        self,
        app,
        state,
        camera_id,
        zone_id,
        track_id,
        vehicle_type,
        action,
        confidence,
        source_type,
    ):
        self._save_log(
            app=app,
            camera_id=camera_id,
            zone_id=zone_id,
            track_id=track_id,
            vehicle_type=vehicle_type,
            action=action,
            confidence=confidence,
            source_type=source_type,
        )

        zone_count = state["zone_counts"].setdefault(
            zone_id,
            {"total": 0, "in": 0, "out": 0}
        )

        if action == "ENTER":
            zone_count["total"] += 1
            zone_count["in"] += 1

        elif action == "EXIT":
            zone_count["out"] += 1

    def _process_movement(
        self,
        app,
        state,
        camera_id,
        track_id,
        current_zone,
        vehicle_type,
        confidence,
        source_type,
    ):
        if track_id is None:
            return

        previous_zone = state["track_last_zones"].get(track_id)

        if current_zone is None:
            if previous_zone is not None:
                state["track_outside_frames"][track_id] = (
                    state["track_outside_frames"].get(track_id, 0) + 1
                )

                if (
                    state["track_outside_frames"][track_id]
                    >= self.OUTSIDE_ROI_TOLERANCE
                ):
                    self._record_event(
                        app, state, camera_id,
                        previous_zone, track_id,
                        vehicle_type, "EXIT",
                        confidence, source_type
                    )

                    state["track_last_zones"].pop(track_id, None)
                    state["track_outside_frames"].pop(track_id, None)

            return

        # Kendaraan kembali masuk ROI.
        state["track_outside_frames"][track_id] = 0

        # Pertama kali kendaraan memasuki salah satu ROI.
        if previous_zone is None:
            self._record_event(
                app, state, camera_id,
                current_zone, track_id,
                vehicle_type, "ENTER",
                confidence, source_type
            )

            state["track_last_zones"][track_id] = current_zone
            return

        # Kendaraan masih berada di zona yang sama.
        if previous_zone == current_zone:
            return

        # Kendaraan berpindah dari satu zona ke zona lain.
        self._record_event(
            app, state, camera_id,
            previous_zone, track_id,
            vehicle_type, "EXIT",
            confidence, source_type
        )

        self._record_event(
            app, state, camera_id,
            current_zone, track_id,
            vehicle_type, "ENTER",
            confidence, source_type
        )

        movement_key = f"{previous_zone}->{current_zone}"

        state["movement_counts"][movement_key] = (
            state["movement_counts"].get(movement_key, 0) + 1
        )

        state["movements"].append({
            "track_id": track_id,
            "vehicle_type": vehicle_type,
            "source_zone": previous_zone,
            "destination_zone": current_zone,
            "movement": movement_key,
            "confidence": round(confidence, 3),
        })

        if len(state["movements"]) > 1000:
            state["movements"] = state["movements"][-1000:]

        state["track_last_zones"][track_id] = current_zone

    def _cleanup_lost_tracks(
        self,
        app,
        state,
        camera_id,
        active_track_ids,
        source_type,
    ):
        current_frame = state["frame_index"]

        for track_id in list(state["track_last_seen"].keys()):
            if track_id in active_track_ids:
                continue

            last_seen = state["track_last_seen"][track_id]

            if current_frame - last_seen < self.LOST_TRACK_TOLERANCE:
                continue

            last_zone = state["track_last_zones"].get(track_id)

            if last_zone is not None:
                self._record_event(
                    app, state, camera_id,
                    last_zone, track_id,
                    state.get("track_types", {}).get(track_id, "Tidak diketahui"),
                    "EXIT",
                    state.get("track_confidences", {}).get(track_id, 0.0),
                    source_type,
                )

            state["track_last_seen"].pop(track_id, None)
            state["track_last_zones"].pop(track_id, None)
            state["track_outside_frames"].pop(track_id, None)

            state.get("track_types", {}).pop(track_id, None)
            state.get("track_confidences", {}).pop(track_id, None)

    def annotate(
        self,
        frame,
        camera_id="default",
        roi_zones=None,
        source_type="LIVE_CCTV",
        app=None,
    ):
        with self.lock:
            self._load_model()

            if self.model is None or frame is None:
                if frame is not None:
                    self._get_state(camera_id)["error"] = self.model_error
                return frame

            try:
                state = self._get_state(camera_id)

                state.setdefault("track_types", {})
                state.setdefault("track_confidences", {})

                state["error"] = None
                state["frame_index"] += 1

                self._sync_zones(state, roi_zones or [])

                predictor = getattr(self.model, 'predictor', None)
                shape = frame.shape[:2]
                if self.frame_shapes.get(camera_id) != shape:
                    self.trackers_by_camera.pop(camera_id, None)
                    self.frame_shapes[camera_id] = shape
                if predictor is not None:
                    saved = self.trackers_by_camera.get(camera_id)
                    if saved is not None:
                        predictor.trackers = saved
                    elif hasattr(predictor, 'trackers'):
                        del predictor.trackers
                results = self.model.track(
                    frame,
                    conf=self.confidence,
                    iou=0.70,
                    imgsz=1280,
                    classes=[0, 1, 2, 3],
                    max_det=300,
                    persist=True,
                    verbose=False,
                )
                predictor = getattr(self.model, 'predictor', None)
                if predictor is not None and hasattr(predictor, 'trackers'):
                    self.trackers_by_camera[camera_id] = predictor.trackers

                return self._draw_results(
                    frame,
                    results,
                    camera_id,
                    app,
                    source_type,
                )

            except Exception as error:
                self._get_state(camera_id)["error"] = str(error)
                print(f"YOLO gagal memproses frame: {error}")
                return frame

    def _draw_results(
        self,
        frame,
        results,
        camera_id,
        app,
        source_type,
    ):
        state = self._get_state(camera_id)
        detections = []
        active_track_ids = set()

        frame_height, frame_width = frame.shape[:2]

        for result in results:
            boxes = getattr(result, "boxes", None)

            if boxes is None:
                continue

            track_ids = boxes.id

            for index, box in enumerate(boxes):
                coordinates = box.xyxy[0].tolist()

                x1, y1, x2, y2 = [
                    int(value) for value in coordinates
                ]

                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())

                label = self.CLASS_NAMES.get(class_id)

                if label is None:
                    continue

                track_id = (
                    int(track_ids[index].item())
                    if track_ids is not None
                    else None
                )

                count_key = self.CLASS_KEYS[label]

                if track_id is not None:
                    active_track_ids.add(track_id)

                    state["track_last_seen"][track_id] = (
                        state["frame_index"]
                    )

                    state["track_types"][track_id] = label
                    state["track_confidences"][track_id] = confidence

                    if track_id not in state["seen_ids"]:
                        state["seen_ids"].add(track_id)
                        state["total"] += 1
                        state[count_key] += 1

                # Titik deteksi menggunakan bottom-center bounding box.
                center_x = (x1 + x2) / 2
                bottom_y = y2

                current_zone = None

                for zone in state["zones"]:
                    zone_id = zone.get("zone_id")

                    if not zone_id or track_id is None:
                        continue

                    if self._is_detection_in_zone(
                        center_x,
                        bottom_y,
                        zone["points"],
                        frame_width,
                        frame_height,
                    ):
                        current_zone = zone_id
                        break

                self._process_movement(
                    app,
                    state,
                    camera_id,
                    track_id,
                    current_zone,
                    label,
                    confidence,
                    source_type,
                )

                color = self.COLORS[label]

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2,
                )

                text = (
                    f"{label} "
                    f"#{track_id if track_id is not None else '-'} "
                    f"{confidence:.0%}"
                )

                text_y = max(y1 - 8, 18)

                cv2.putText(
                    frame,
                    text,
                    (x1, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                    cv2.LINE_AA,
                )

                detections.append({
                    "track_id": track_id,
                    "label": label,
                    "class": count_key,
                    "confidence": round(confidence, 3),
                    "box": [x1, y1, x2, y2],
                    "zone_id": current_zone,
                })

        state["detections"] = detections

        self._cleanup_lost_tracks(
            app,
            state,
            camera_id,
            active_track_ids,
            source_type,
        )

        return frame

    @staticmethod
    def _is_detection_in_zone(
        x,
        y,
        points,
        frame_width,
        frame_height,
    ):
        polygon = [
            (
                point[0] * frame_width,
                point[1] * frame_height,
            )
            for point in points
        ]

        inside = False
        previous = len(polygon) - 1

        for current, (point_x, point_y) in enumerate(polygon):
            previous_x, previous_y = polygon[previous]

            if (
                (point_y > y) != (previous_y > y)
                and x < (
                    (previous_x - point_x)
                    * (y - point_y)
                    / (previous_y - point_y)
                    + point_x
                )
            ):
                inside = not inside

            previous = current

        return inside

    def get_state(self, camera_id):
        with self.lock:
            state = self._get_state(camera_id)

            return {
                "total": state["total"],
                "car": state["car"],
                "motorcycle": state["motorcycle"],
                "bus": state["bus"],
                "truck": state["truck"],
                "detections": list(state["detections"]),
                "error": state["error"],
                "movement_counts": dict(state["movement_counts"]),
                "movements": list(state["movements"][-100:]),
                "zone_counts": {
                    zone.get("zone_id"): {
                        **state["zone_counts"].get(
                            zone.get("zone_id"),
                            {"total": 0, "in": 0, "out": 0},
                        ),
                        "name": zone.get(
                            "zone_name",
                            zone.get("zone_id"),
                        ),
                        "color": zone.get("color", "#06b6d4"),
                    }
                    for zone in state["zones"]
                    if zone.get("zone_id")
                },
            }


    def reset_counts(self, camera_id):
        """Kosongkan hitungan di memori. Zona dan ingatan tracker tidak disentuh."""
        with self.lock:
            state = self._get_state(camera_id)
            state["total"] = 0
            state["car"] = 0
            state["motorcycle"] = 0
            state["bus"] = 0
            state["truck"] = 0
            state["seen_ids"].clear()
            for zone_id in state["zone_counts"]:
                state["zone_counts"][zone_id] = {"total": 0, "in": 0, "out": 0}
            for zone_id in state["zone_seen_ids"]:
                state["zone_seen_ids"][zone_id] = set()
            state["movement_counts"] = {}
            state["movements"] = []


vehicle_detector = VehicleDetector()


def annotate_frame(
    frame,
    camera_id="default",
    roi_zones=None,
    source_type="LIVE_CCTV",
    app=None,
):
    return vehicle_detector.annotate(
        frame,
        camera_id,
        roi_zones,
        source_type,
        app,
    )


def get_detection_state(camera_id):
    return vehicle_detector.get_state(camera_id)


def reset_detection_state(camera_id):
    vehicle_detector.reset_counts(camera_id)
