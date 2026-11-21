from flask import Blueprint, request, jsonify, session

from app.services.auth_service import verify_user


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "message": "Request body wajib diisi"
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username dan password wajib diisi"
        }), 400

    user = verify_user(username, password)

    if not user:
        return jsonify({
            "status": "error",
            "message": "Username atau password salah"
        }), 401

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    return jsonify({
        "status": "success",
        "message": "Login berhasil",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }), 200

@auth_bp.route("/check", methods=["GET"])
def check_login():
    if "user_id" not in session:
        return jsonify({
            "status": "error",
            "logged_in": False,
            "message": "Belum login"
        }), 401

    return jsonify({
        "status": "success",
        "logged_in": True,
        "user": {
            "id": session["user_id"],
            "username": session["username"],
            "role": session["role"]
        }
    }), 200

@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    session.modified = True

    response = jsonify({
        "status": "success",
        "message": "Logout berhasil"
    })
    response.delete_cookie("session", path="/")
    return response, 200