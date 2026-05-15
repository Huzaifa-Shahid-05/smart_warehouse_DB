"""
Logging setup — rotating file handler + console output.
"""
import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(app, cfg):
    """Attach a rotating file handler and stream handler to the Flask app logger."""
    log_dir  = getattr(cfg, "LOG_DIR", "logs")
    max_bytes = getattr(cfg, "LOG_MAX_BYTES", 10 * 1024 * 1024)
    backups   = getattr(cfg, "LOG_BACKUPS", 5)
    debug     = getattr(cfg, "DEBUG", False)

    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler
    log_path = os.path.join(log_dir, "smart_warehouse.log")
    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)

    # Also quiet down noisy werkzeug in production
    if not debug:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app.logger.info("Smart Warehouse logging initialized.")
