from app.extensions import db


class CameraSource(db.Model):
    __tablename__ = "camera_sources"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    camera_id = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

    rtsp_url = db.Column(
        db.Text,
        nullable=True
    )

    default_video_path = db.Column(
        db.Text,
        nullable=False
    )

    current_source = db.Column(
        db.String(20),
        nullable=False,
        default="DEFAULT_LOOP"
    )

    last_checked_at = db.Column(
        db.DateTime,
        nullable=True
    )

    last_online_at = db.Column(
        db.DateTime,
        nullable=True
    )