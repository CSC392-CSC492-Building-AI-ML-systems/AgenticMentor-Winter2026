"""Logging helpers for the project."""

from __future__ import annotations

import logging


def get_logger(name: str = "agentic_project") -> logging.Logger:
    """Return a configured logger instance."""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)
