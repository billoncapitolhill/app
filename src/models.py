from dataclasses import dataclass
from typing import Optional

@dataclass
class Bill:
    congress: int
    type: str
    number: str
    id: Optional[str] = None
    # Add other relevant fields as needed 