import numpy as np
from collections import defaultdict, OrderedDict
import math

class CentroidTracker:
    """
    Tracker berdasarkan centroid untuk melacak kendaraan dan menghitung yang melewati detection line
    """
    def __init__(self, maxDisappeared=50):
        self.nextObjectID = 0
        self.objects = OrderedDict()  # ID -> (cx, cy)
        self.disappeared = OrderedDict()  # ID -> frame count
        self.vehicle_classes = OrderedDict()  # ID -> class
        self.detected_vehicles = defaultdict(int)  # class -> count
        self.crossed_line = set()  # ID yang sudah melewati detection line
        self.maxDisappeared = maxDisappeared

    def register(self, centroid, vehicle_class):
        """Register object baru dengan ID unik"""
        self.objects[self.nextObjectID] = centroid
        self.disappeared[self.nextObjectID] = 0
        self.vehicle_classes[self.nextObjectID] = vehicle_class
        self.nextObjectID += 1

    def deregister(self, objectID):
        """Hapus object yang sudah tidak terdeteksi"""
        del self.objects[objectID]
        del self.disappeared[objectID]
        del self.vehicle_classes[objectID]

    def update(self, rects, vehicle_classes_list):
        """
        Update tracker dengan deteksi baru
        
        Args:
            rects: list of (x1, y1, x2, y2) bounding boxes
            vehicle_classes_list: list of vehicle classes sesuai rects
        """
        if len(rects) == 0:
            # Increment disappeared untuk semua object yang ada
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)
            return self.objects, self.detected_vehicles

        # Hitung centroid dari bounding boxes
        inputCentroids = np.zeros((len(rects), 2), dtype="int")
        for i, (x1, y1, x2, y2) in enumerate(rects):
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            inputCentroids[i] = (cx, cy)

        # Jika belum ada object, register semua sebagai object baru
        if len(self.objects) == 0:
            for i in range(0, len(inputCentroids)):
                self.register(inputCentroids[i], vehicle_classes_list[i])
        else:
            # Match centroid baru dengan yang lama
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            # Hitung euclidean distance
            D = self._distance_matrix(np.array(objectCentroids), inputCentroids)

            # Cari matching terbaik
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            usedRows = set()
            usedCols = set()

            for row, col in zip(rows, cols):
                if row in usedRows or col in usedCols:
                    continue
                if D[row, col] > 50:  # Threshold distance
                    continue

                objectID = objectIDs[row]
                self.objects[objectID] = inputCentroids[col]
                self.disappeared[objectID] = 0
                self.vehicle_classes[objectID] = vehicle_classes_list[col]

                usedRows.add(row)
                usedCols.add(col)

            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)

            # Jika lebih banyak object yang ada, update disappeared
            if D.shape[0] >= D.shape[1]:
                for row in unusedRows:
                    objectID = objectIDs[row]
                    self.disappeared[objectID] += 1
                    if self.disappeared[objectID] > self.maxDisappeared:
                        self.deregister(objectID)
            # Jika lebih banyak centroid baru, register sebagai object baru
            else:
                for col in unusedCols:
                    self.register(inputCentroids[col], vehicle_classes_list[col])

        return self.objects, self.detected_vehicles

    def check_line_crossing(self, line_start, line_end):
        """
        Check apakah ada object yang melewati detection line
        
        Args:
            line_start: tuple (x1, y1)
            line_end: tuple (x2, y2)
        """
        for objectID, centroid in self.objects.items():
            if objectID not in self.crossed_line:
                if self._point_to_line_distance(centroid, line_start, line_end) < 10:
                    self.crossed_line.add(objectID)
                    vehicle_class = self.vehicle_classes[objectID]
                    self.detected_vehicles[vehicle_class] += 1

    def _distance_matrix(self, A, B):
        """Hitung distance matrix antara dua set centroid"""
        distances = np.zeros((A.shape[0], B.shape[0]))
        for i in range(A.shape[0]):
            for j in range(B.shape[0]):
                distances[i, j] = np.linalg.norm(A[i] - B[j])
        return distances

    def _point_to_line_distance(self, point, line_start, line_end):
        """Hitung jarak dari point ke line"""
        px, py = point
        x1, y1 = line_start
        x2, y2 = line_end

        # Jarak perpendicular dari point ke line
        numerator = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
        denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
        
        if denominator == 0:
            return float('inf')
        
        return numerator / denominator

    def get_vehicle_count(self):
        """Get total count untuk setiap jenis kendaraan"""
        return dict(self.detected_vehicles)

    def reset_crossed_line(self):
        """Reset list kendaraan yang sudah melewati line"""
        self.crossed_line = set()
