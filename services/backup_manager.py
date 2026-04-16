import logging
import asyncio
import shutil
import gzip
import os
from pathlib import Path
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, db_path: Path, backup_dir: Path = Path("storage/backups")):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 5

    async def create_backup(self) -> Path:
        if not self.db_path.exists():
            raise FileNotFoundError("Database file not found")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"bot_{timestamp}.db.gz"
        
        def _compress():
            temp_db = self.backup_dir / "temp.db"
            shutil.copy2(self.db_path, temp_db)
            with open(temp_db, "rb") as f_in:
                with gzip.open(backup_file, "wb", compresslevel=5) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            temp_db.unlink(missing_ok=True)

        await asyncio.to_thread(_compress)
        
        # Rotate backups
        backups = sorted(self.backup_dir.glob("bot_*.db.gz"))
        for old_backup in backups[:-self.max_backups]:
            old_backup.unlink(missing_ok=True)
            
        logger.info(f"Backup created: {backup_file}")
        return backup_file

    async def upload_to_s3(self, backup_path: Path, bucket: str = "your-backup-bucket") -> bool:
        if not backup_path.exists():
            return False
        try:
            import boto3
            def _upload():
                s3 = boto3.client("s3", region_name=settings.AWS_REGION)
                s3.upload_file(str(backup_path), bucket, f"backups/{backup_path.name}")
            await asyncio.to_thread(_upload)
            logger.info(f"Uploaded {backup_path.name} to S3 bucket {bucket}")
            return True
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

backup_manager = BackupManager(settings.DB_PATH)