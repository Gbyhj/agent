"""统一日志器"""
import sys, os, logging
from datetime import datetime

_logger = None

def get_logger(name: str = "agent") -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        level = getattr(logging, os.getenv("AGENT_LOG", "INFO"), logging.INFO)
        _logger.setLevel(level)
        if not _logger.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            ))
            _logger.addHandler(h)
    return _logger

def info(msg: str, *args): get_logger().info(msg, *args)
def warn(msg: str, *args): get_logger().warning(msg, *args)
def error(msg: str, *args): get_logger().error(msg, *args)
