#!/usr/bin/env python3
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

__version__ = "0.0.1"
__author__ = "Karie Moorman"

_logging_configured = False


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the entire ghostbit package"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_dir / "ghostbit.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console_handler.setFormatter(detailed_formatter if verbose else simple_formatter)

    root_logger = logging.getLogger("ghostbit")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.propagate = False

    _logging_configured = True
