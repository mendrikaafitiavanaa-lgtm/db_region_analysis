"""Un fichier de log par exécution, sous logs/run_YYYY-MM-DD_HHhMM.log."""
import logging
import os
from datetime import datetime

from config import settings


def get_logger(name: str = "enrichment") -> logging.Logger:
    os.makedirs(settings.LOGS_DIR, exist_ok=True)
    filename = datetime.now().strftime("run_%Y-%m-%d_%Hh%M.log")
    filepath = os.path.join(settings.LOGS_DIR, filename)

    logger = logging.getLogger(name)
    if logger.handlers:  # évite les handlers dupliqués si appelé plusieurs fois
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(filepath, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
