
import math

from flask import Blueprint, request
from app.extensions import db
from app.models import ROIConfiguration

roi_bp = Blueprint(
    "roi",
    __name__,
    url_prefix="/api/cameras"
)


def validate_roi_zones(roi_zones):
    if not isinstance(roi_zones, list):
        return "roi_zones harus berupa list"

    used_ids = set()

    for index, zone in enumerate(roi_zones):
        if not isinstance(zone, dict):
            return f"Zona ke-{index + 1} harus berupa object"

        zone_id = zone.get("zone_id")
        zone_name = zone.get("zone_name")
        points = zone.get("points")

        if not isinstance(zone_id, str) or not zone_id.strip():
            return f"zone_id pada zona ke-{index + 1} wajib diisi"

        if zone_id in used_ids:
            return f"zone_id '{zone_id}' tidak boleh duplikat"

        used_ids.add(zone_id)

        if not isinstance(zone_name, str) or not zone_name.strip():
            return f"zone_name pada zona {zone_id} wajib diisi"

        if not isinstance(points, list) or len(points) < 3:
            return f"Zona {zone_id} harus memiliki minimal 3 titik"

        for point_index, point in enumerate(points):
            if not isinstance(point, list) or len(point) != 2:
                return (
                    f"Titik ke-{point_index + 1} pada zona {zone_id} "
                    "harus memiliki format [x, y]"
                )

            x, y = point

            if (
                isinstance(x, bool)
                or isinstance(y, bool)
                or not isinstance(x, (int, float))
                or not isinstance(y, (int, float))
            ):
                return f"Koordinat zona {zone_id} harus berupa angka"

            if not math.isfinite(x) or not math.isfinite(y):
                return f"Koordinat zona {zone_id} harus berupa angka valid"

            if not (0 <= x <= 1 and 0 <= y <= 1):
                return (
                    f"Koordinat zona {zone_id} harus berada "
                    "di antara 0 dan 1"
                )

    return None


@roi_bp.post("/<camera_id>/roi")
def save_roi(camera_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "status": "error",
            "message": "Request body harus berupa JSON object"
        }, 400

    roi_zones = data.get("roi_zones")

    error = validate_roi_zones(roi_zones)

    if error:
        return {
            "status": "error",
            "message": error
        }, 400

    roi_config = ROIConfiguration.query.filter_by(
        camera_id=camera_id
    ).first()

    if roi_config:
        roi_config.roi_zones = roi_zones
    else:
        roi_config = ROIConfiguration(
            camera_id=camera_id,
            roi_zones=roi_zones
        )
        db.session.add(roi_config)

    db.session.commit()

    return {
        "status": "success",
        "message": "ROI berhasil disimpan",
        "data": {
            "camera_id": camera_id,
            "roi_zones": roi_config.roi_zones
        }
    }, 200


@roi_bp.get("/<camera_id>/roi")
def get_roi(camera_id):
    roi_config = ROIConfiguration.query.filter_by(
        camera_id=camera_id
    ).first()

    if not roi_config:
        return {
            "status": "error",
            "message": "ROI untuk camera tersebut belum ditemukan"
        }, 404

    return {
        "status": "success",
        "data": {
            "camera_id": roi_config.camera_id,
            "roi_zones": roi_config.roi_zones,
            "updated_at": roi_config.updated_at
        }
    }, 200
