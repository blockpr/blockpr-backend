from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class UsageRecord:
    id: UUID
    user_id: UUID
    month: Optional[int]
    year: Optional[int]
    certificates_generated: int
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "UsageRecord":
        """Create UsageRecord from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            month=data.get("month"),
            year=data.get("year"),
            certificates_generated=data.get("certificates_generated", 0),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert UsageRecord to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "month": self.month,
            "year": self.year,
            "certificates_generated": self.certificates_generated,
            "created_at": self.created_at.isoformat(),
        }
