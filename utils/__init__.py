"""
Logging System — 替换 print() 为结构化日志

用法:
    from agent.utils.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Agent started")
    logger.error("Tool failed", extra={"tool": "bash", "error": "timeout"})
"""
from __future__ import annotations

import os
import sys
import logging
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式"""
    COLORS = {
        "DEBUG": "\033[36m",   # CYAN
        "INFO": "\033[32m",    # GREEN
        "WARNING": "\033[33m", # YELLOW
        "ERROR": "\033[31m",   # RED
        "CRITICAL": "\033[35m",# MAGENTA
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """获取结构化日志器"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        level = level or os.environ.get("AGENT_LOG_LEVEL", "INFO")
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        handler = logging.StreamHandler(sys.stderr)
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        formatter = ColoredFormatter(fmt, datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# 默认日志器
logger = get_logger("agent")
