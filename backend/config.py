import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 3306))
    DB_USER     = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME     = os.getenv("DB_NAME", "smart_warehouse")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE        = 280
    SQLALCHEMY_POOL_PRE_PING       = True

    JWT_SECRET_KEY            = os.getenv(
        "JWT_SECRET_KEY",
        "smart-warehouse-super-secret-jwt-key-2026-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES  = int(os.getenv("JWT_ACCESS_EXPIRES",  3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_EXPIRES", 604800))
    JWT_TOKEN_LOCATION        = ["headers"]
    JWT_HEADER_NAME           = "Authorization"
    JWT_HEADER_TYPE           = "Bearer"
    JWT_DECODE_ALGORITHMS     = ["HS256"]

    MAX_FAILED_LOGINS = int(os.getenv("MAX_FAILED_LOGINS", 5))
    LOCKOUT_MINUTES   = int(os.getenv("LOCKOUT_MINUTES", 15))
    BCRYPT_ROUNDS     = int(os.getenv("BCRYPT_ROUNDS", 4))

    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000"
    ).split(",")

    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"

    DEFAULT_PAGE     = 1
    DEFAULT_PER_PAGE = 25
    MAX_PER_PAGE     = 100

    LOG_DIR       = os.getenv("LOG_DIR", "logs")
    LOG_MAX_BYTES = 10 * 1024 * 1024
    LOG_BACKUPS   = 5

    REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")

class DevelopmentConfig(Config):
    DEBUG         = True
    BCRYPT_ROUNDS = 4

class ProductionConfig(Config):
    DEBUG = False

config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
