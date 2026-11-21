from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    try:
        db.session.execute(db.text("SELECT 1"))
        print("Koneksi database berhasil!")
    except Exception as e:
        print("Koneksi database gagal!")
        print(e)