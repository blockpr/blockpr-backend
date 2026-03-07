from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Subscription:
    id: UUID
    user_id: UUID
    tier_id: UUID
    status: Optional[str]
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        """Create Subscription from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            tier_id=data["tier_id"],
            status=data.get("status"),
            current_period_start=data.get("current_period_start"),
            current_period_end=data.get("current_period_end"),
            cancel_at_period_end=data.get("cancel_at_period_end", False),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert Subscription to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "tier_id": str(self.tier_id),
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "created_at": self.created_at.isoformat(),
        }
