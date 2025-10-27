from loguru import logger
import sys

def setup_logger():
    logger.remove()
    logger.add(sys.stdout, format="<green>[{time:HH:mm:ss}]</green> <level>{message}</level>", level="INFO")
    return logger
