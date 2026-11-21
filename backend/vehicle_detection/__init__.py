"""
Vehicle Detection System Package
"""

__version__ = "1.0.0"
__author__ = "Vehicle Detection Team"
__description__ = "Real-time vehicle detection and counting system"

from vehicle_detection.vehicle_detector import VehicleDetector
from vehicle_detection.centroid_tracker import CentroidTracker

__all__ = [
    'VehicleDetector',
    'CentroidTracker'
]
