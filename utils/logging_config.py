import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging(level: str = "INFO", log_dir: str = "logs", max_bytes: int = 10_485_760, backup_count: int = 3):
    Path(log_dir).mkdir(exist_ok=True)
    log_file = Path(log_dir) / "bot.log"
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if root.handlers:
        root.handlers.clear()
        
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)