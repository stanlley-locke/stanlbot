import re
import logging
from pathlib import Path
from typing import List, Dict
from dateutil import parser as dateparser

logger = logging.getLogger(__name__)

class WhatsAppParser:
    MSG_REGEX = re.compile(r"^\[(\d{2}/\d{2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)]\s*(.*?):\s*(.*)")
    MEDIA_REGEX = re.compile(r"<attached:\s*(.*)>", re.IGNORECASE)

    def parse_file(self, file_path: str) -> List[Dict[str, str]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Export file not found: {file_path}")
            
        messages = []
        current_msg = None
        
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                match = self.MSG_REGEX.match(line)
                if match:
                    if current_msg:
                        messages.append(current_msg)
                    date_str, time_str, sender, text = match.groups()
                    dt_str = f"{date_str}, {time_str}"
                    try:
                        dt = dateparser.parse(dt_str, fuzzy=True)
                    except ValueError:
                        dt = None
                        
                    current_msg = {
                        "timestamp": str(dt),
                        "sender": sender.strip(),
                        "content": self.MEDIA_REGEX.sub("[MEDIA]", text.strip()),
                        "is_media": bool(self.MEDIA_REGEX.search(text))
                    }
                elif current_msg:
                    current_msg["content"] += f"\n{line}"
                    
        if current_msg:
            messages.append(current_msg)
            
        logger.info(f"Parsed {len(messages)} messages from {path.name}")
        return messages