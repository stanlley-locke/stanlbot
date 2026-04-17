import re
from typing import List, Union

TAG_PATTERN = re.compile(r"^[a-z0-9_\-]{1,20}$")

def sanitize_input(text: str, max_len: int = 1000) -> str:
    text = "".join(c for c in text if c.isprintable() or c in ("\n", " "))
    return text.strip()[:max_len]

def validate_tags(raw_input: Union[str, List[str]]) -> List[str]:
    """Parses and validates tags from a comma-separated string or list."""
    if not raw_input:
        return []
        
    # Handle "skip"
    if isinstance(raw_input, str) and raw_input.lower().strip() == "skip":
        return []
    
    # Normalize to list
    if isinstance(raw_input, str):
        parts = raw_input.split(",")
    else:
        parts = raw_input
        
    valid = []
    for tag in parts:
        cleaned = tag.strip().lower().replace(" ", "_")
        if TAG_PATTERN.match(cleaned) and len(valid) < 10:
            valid.append(cleaned)
    return valid

def parse_command_args(text: str) -> tuple[str, str]:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lstrip("/") if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args