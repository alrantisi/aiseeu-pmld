from app.extensions import db


class VehicleLog(db.Model):
    __bind_key__ = "data"
    __tablename__ = "vehicle_logs"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    camera_id = db.Column(
        db.String(50),
        nullable=False
    )

    zone_id = db.Column(
        db.String(50),
        nullable=False
    )

    zone_name = db.Column(
        db.String(100),
        nullable=False
    )

    track_id = db.Column(
        db.Integer,
        nullable=False
    )

    vehicle_type = db.Column(
        db.String(30),
        nullable=False
    )

    action = db.Column(
        db.String(10),
        nullable=False
    )

    confidence = db.Column(
        db.Float,
        nullable=False
    )

    source_type = db.Column(
        db.String(20),
        nullable=False,
        default="LIVE_CCTV"
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )