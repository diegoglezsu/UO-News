#!/usr/bin/env python3
"""
Sistema de logging con archivos rotativos.
"""

import logging
import logging.handlers

from config.settings import LOG_DIR, LOG_LEVEL


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(console)

    app_file = logging.handlers.RotatingFileHandler(
        LOG_DIR / "uo-news.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_file.setLevel(level)
    app_file.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(app_file)

    error_file = logging.handlers.RotatingFileHandler(
        LOG_DIR / "uo-news-errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(error_file)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
