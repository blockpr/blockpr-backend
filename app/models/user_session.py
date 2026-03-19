from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class UserSession:
    id: int
    user_id: Optional[UUID]
    device_name: Optional[str]
    device_specs: Optional[str]
    action: Optional[str]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "UserSession":
        return cls(
            id=data["id"],
            user_id=data.get("user_id"),
            device_name=data.get("device_name"),
            device_specs=data.get("device_specs"),
            action=data.get("action"),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": str(self.user_id) if self.user_id else None,
            "device_name": self.device_name,
            "device_specs": self.device_specs,
            "action": self.action,
            "created_at": self.created_at.isoformat(),
        }
