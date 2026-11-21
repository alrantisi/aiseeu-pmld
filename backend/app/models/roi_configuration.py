from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class ROIConfiguration(db.Model):
    __tablename__ = "roi_configurations"

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

    roi_zones = db.Column(
        JSONB,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )