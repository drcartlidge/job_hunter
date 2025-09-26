# models.py
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class Job:
    company: str
    title: str
    location: Optional[str]
    url: str
    description: str
    raw: Dict[str, Any]

    def __repr__(self):
        return f"<Job {self.title} at {self.company}>"
