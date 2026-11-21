from getpass import getpass

from app import create_app
from app.services.auth_service import create_user


password = getpass("Password admin baru: ")
confirm = getpass("Ulangi password: ")

if not password or password != confirm:
    raise SystemExit("Password kosong atau tidak sama. Dibatalkan.")

app = create_app()

with app.app_context():
    user = create_user(
        username="admin",
        password=password,
        role="admin"
    )

    if user:
        print("Akun admin berhasil dibuat.")
    else:
        print("Username admin sudah ada.")
