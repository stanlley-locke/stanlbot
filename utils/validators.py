import re
from typing import List, Tuple

TAG_PATTERN = re.compile(r"^[a-z0-9_\-]{1,20}$")

def sanitize_input(text: str, max_len: int = 1000) -> str:
    text = "".join(c for c in text if c.isprintable() or c in ("\n", " "))
    return text.strip()[:max_len]

def validate_tags(raw_tags: str) -> List[str]:
    if not raw_tags or raw_tags.lower() == "skip":
        return []
    tags = raw_tags.split(",")
    valid = []
    for tag in tags:
        cleaned = tag.strip().lower().replace(" ", "_")
        if TAG_PATTERN.match(cleaned) and len(valid) < 10:
            valid.append(cleaned)
    return valid

def parse_command_args(text: str) -> Tuple[str, str]:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lstrip("/") if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args