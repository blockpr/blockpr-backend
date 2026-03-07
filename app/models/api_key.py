from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class ApiKey:
    id: UUID
    user_id: UUID
    key_hash: str
    name: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]

    @classmethod
    def from_dict(cls, data: dict) -> "ApiKey":
        """Create ApiKey from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            key_hash=data["key_hash"],
            name=data.get("name"),
            created_at=data["created_at"],
            last_used_at=data.get("last_used_at"),
        )

    def to_dict(self) -> dict:
        """Convert ApiKey to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "key_hash": self.key_hash,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
