from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Webhook:
    id: UUID
    user_id: UUID
    url: str
    secret: Optional[str]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Webhook":
        """Create Webhook from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            url=data["url"],
            secret=data.get("secret"),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert Webhook to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "url": self.url,
            "secret": self.secret,
            "created_at": self.created_at.isoformat(),
        }
