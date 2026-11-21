from app import create_app
from app.extensions import db

from app.models import ROIConfiguration, CameraSource, VehicleLog

app = create_app()

with app.app_context():
    # Membuat tabel pada database management
    db.create_all()

    # Membuat tabel pada database data
    db.create_all(bind_key="data")

    print("Semua tabel berhasil dibuat!")