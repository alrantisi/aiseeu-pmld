
from flask import Blueprint, request, session
from sqlalchemy import func

from app.models import VehicleLog
from app.extensions import db


log_bp = Blueprint(
    "logs",
    __name__,
    url_prefix="/api/logs"
)


def apply_log_filters(query):
    """
    Menerapkan filter kamera dan sumber video
    pada query log kendaraan.
    """

    camera_id = request.args.get("camera_id")
    source_type = request.args.get("source_type")

    if camera_id:
        query = query.filter(
            VehicleLog.camera_id == camera_id
        )

    if source_type:
        source_type = source_type.upper()

        if source_type not in ["LIVE_CCTV", "DEFAULT_LOOP"]:
            return None, {
                "status": "error",
                "message": "source_type harus LIVE_CCTV atau DEFAULT_LOOP"
            }, 400

        query = query.filter(
            VehicleLog.source_type == source_type
        )

    return query, None, None


@log_bp.get("")
def get_vehicle_logs():
    try:
        # Parameter pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        if page < 1 or per_page < 1:
            return {
                "status": "error",
                "message": "page dan per_page harus lebih dari 0"
            }, 400

        # Batasi jumlah data per halaman
        per_page = min(per_page, 100)

        # Query dasar
        query = VehicleLog.query

        # Filter berdasarkan parameter URL
        camera_id = request.args.get("camera_id")
        track_id = request.args.get("track_id", type=int)
        zone_id = request.args.get("zone_id")
        action = request.args.get("action")

        if camera_id:
            query = query.filter(
                VehicleLog.camera_id == camera_id
            )

        if track_id is not None:
            query = query.filter(
                VehicleLog.track_id == track_id
            )

        if zone_id:
            query = query.filter(
                VehicleLog.zone_id == zone_id
            )

        if action:
            action = action.upper()

            if action not in ["ENTER", "EXIT"]:
                return {
                    "status": "error",
                    "message": "action harus ENTER atau EXIT"
                }, 400

            query = query.filter(
                VehicleLog.action == action
            )

        # Filter sumber video
        query, error_response, error_code = apply_log_filters(query)

        if error_response:
            return error_response, error_code

        # Urutkan data terbaru terlebih dahulu
        query = query.order_by(
            VehicleLog.created_at.desc(),
            VehicleLog.id.desc()
        )

        # Hitung total data sesuai filter
        total = query.count()

        # Ambil data berdasarkan halaman
        logs = query.offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        result = []

        for log in logs:
            result.append({
                "id": log.id,
                "camera_id": log.camera_id,
                "track_id": log.track_id,
                "vehicle_type": log.vehicle_type,
                "zone_id": log.zone_id,
                "zone_name": log.zone_name,
                "action": log.action,
                "confidence": log.confidence,
                "source_type": log.source_type,
                "created_at": (
                    log.created_at.isoformat()
                    if log.created_at else None
                )
            })

        return {
            "status": "success",
            "data": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_data": total,
                "total_pages": (
                    (total + per_page - 1) // per_page
                )
            }
        }, 200

    except Exception as error:
        return {
            "status": "error",
            "message": "Gagal mengambil riwayat kendaraan",
            "detail": str(error)
        }, 500


@log_bp.get("/summary")
def get_vehicle_logs_summary():
    try:
        # Query dasar
        query = VehicleLog.query

        # Terapkan filter kamera dan sumber video
        query, error_response, error_code = apply_log_filters(query)

        if error_response:
            return error_response, error_code

        # Ambil catatan kendaraan berdasarkan waktu dan ID.
        # Catatan pertama untuk setiap track menjadi acuan jenis kendaraan.
        vehicle_rows = (
            query.with_entities(
                VehicleLog.id,
                VehicleLog.camera_id,
                VehicleLog.track_id,
                VehicleLog.vehicle_type
            )
            .order_by(
                VehicleLog.created_at.asc(),
                VehicleLog.id.asc()
            )
            .all()
        )

        # Simpan satu jenis kendaraan untuk setiap track unik.
        unique_vehicles = {}

        for row in vehicle_rows:
            vehicle_key = (
                row.camera_id,
                row.track_id
            )

            if vehicle_key not in unique_vehicles:
                unique_vehicles[vehicle_key] = row.vehicle_type

        # Hitung kendaraan berdasarkan jenis
        vehicle_counts = {
            "Mobil": 0,
            "Motor": 0,
            "Bus": 0,
            "Truk": 0
        }

        for vehicle_type in unique_vehicles.values():
            normalized_type = str(vehicle_type).strip().lower()

            if normalized_type in ["mobil", "car"]:
                vehicle_counts["Mobil"] += 1

            elif normalized_type == "motor":
                vehicle_counts["Motor"] += 1

            elif normalized_type == "bus":
                vehicle_counts["Bus"] += 1

            elif normalized_type == "truk":
                vehicle_counts["Truk"] += 1

        total_unique_vehicles = len(unique_vehicles)

        # Hitung aktivitas ENTER dan EXIT
        activity_rows = (
            query.with_entities(
                VehicleLog.action,
                func.count(VehicleLog.id)
            )
            .group_by(VehicleLog.action)
            .all()
        )

        activity_counts = {
            "ENTER": 0,
            "EXIT": 0
        }

        for action, total in activity_rows:
            if action in activity_counts:
                activity_counts[action] = total

        # Hitung aktivitas berdasarkan zona dan action
        zone_rows = (
            query.with_entities(
                VehicleLog.zone_id,
                VehicleLog.zone_name,
                VehicleLog.action,
                func.count(VehicleLog.id)
            )
            .group_by(
                VehicleLog.zone_id,
                VehicleLog.zone_name,
                VehicleLog.action
            )
            .order_by(VehicleLog.zone_id)
            .all()
        )

        zone_summary = {}

        for zone_id, zone_name, action, total in zone_rows:
            if zone_id not in zone_summary:
                zone_summary[zone_id] = {
                    "zone_name": zone_name,
                    "ENTER": 0,
                    "EXIT": 0
                }

            if action in ["ENTER", "EXIT"]:
                zone_summary[zone_id][action] = total

        # Total seluruh aktivitas
        total_activity = query.count()

        # Filter yang digunakan
        camera_id = request.args.get("camera_id")
        source_type = request.args.get("source_type")

        return {
            "status": "success",
            "data": {
                "total_unique_vehicles": total_unique_vehicles,
                "vehicle_counts": vehicle_counts,
                "total_activity": total_activity,
                "activity_counts": activity_counts,
                "zone_summary": zone_summary
            },
            "filters": {
                "camera_id": camera_id,
                "source_type": (
                    source_type.upper()
                    if source_type else None
                )
            }
        }, 200

    except Exception as error:
        return {
            "status": "error",
            "message": "Gagal mengambil rekap kendaraan",
            "detail": str(error)
        }, 500


@log_bp.delete("")
def delete_vehicle_logs():
    if session.get("role") != "admin":
        return {
            "status": "error",
            "message": "Hanya admin yang boleh menghapus log"
        }, 403

    camera_id = request.args.get("camera_id")
    if not camera_id:
        return {
            "status": "error",
            "message": "camera_id wajib diisi untuk menghapus log"
        }, 400

    data = request.get_json(silent=True)
    ids = data.get("ids") if isinstance(data, dict) else None

    valid = (
        isinstance(ids, list)
        and 0 < len(ids) <= 20000
        and all(isinstance(i, int) and not isinstance(i, bool) for i in ids)
    )
    if not valid:
        return {
            "status": "error",
            "message": "ids harus berupa daftar ID log (tidak boleh kosong)"
        }, 400

    deleted = VehicleLog.query.filter(
        VehicleLog.camera_id == camera_id,
        VehicleLog.id.in_(ids)
    ).delete(synchronize_session=False)
    db.session.commit()

    return {
        "status": "success",
        "message": "Log berhasil dihapus",
        "data": {"deleted": deleted}
    }, 200
