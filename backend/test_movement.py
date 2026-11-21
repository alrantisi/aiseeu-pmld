from ml_engine.vehicle_detector import VehicleDetector

detector = VehicleDetector()

# Buat state kamera pengujian
state = detector._get_state("cam_test")

# Simulasi kendaraan ID 12
print("1. Kendaraan masuk zona A")
detector._process_movement(
    state, 12, "A", "Mobil", 0.90
)

print("2. Kendaraan masih di zona A")
detector._process_movement(
    state, 12, "A", "Mobil", 0.90
)

print("3. Kendaraan berpindah ke zona C")
detector._process_movement(
    state, 12, "C", "Mobil", 0.89
)

print("4. Kendaraan masih di zona C")
detector._process_movement(
    state, 12, "C", "Mobil", 0.89
)

print("5. Kendaraan berpindah ke zona B")
detector._process_movement(
    state, 12, "B", "Mobil", 0.88
)

print("\nHASIL PENGUJIAN")
print("Movement counts:", state["movement_counts"])
print("Movement history:")

for movement in state["movements"]:
    print(movement)