from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class UserToken:
    id: UUID
    user_id: UUID
    token_hash: str
    type: str
    expires_at: datetime
    used: bool
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "UserToken":
        """Create UserToken from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            token_hash=data["token_hash"],
            type=data["type"],
            expires_at=data["expires_at"],
            used=data.get("used", False),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert UserToken to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "token_hash": self.token_hash,
            "type": self.type,
            "expires_at": self.expires_at.isoformat(),
            "used": self.used,
            "created_at": self.created_at.isoformat(),
        }
