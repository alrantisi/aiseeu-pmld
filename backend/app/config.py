import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "MANAGEMENT_DATABASE_URL"
    )

    SQLALCHEMY_BINDS = {
        "data": os.getenv("DATA_DATABASE_URL")
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")