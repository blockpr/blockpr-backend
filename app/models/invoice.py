from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class Invoice:
    id: UUID
    user_id: UUID
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    certificates_count: Optional[int]
    unit_price: Optional[Decimal]
    total: Optional[Decimal]
    status: Optional[str]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Invoice":
        """Create Invoice from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            period_start=data.get("period_start"),
            period_end=data.get("period_end"),
            certificates_count=data.get("certificates_count"),
            unit_price=data.get("unit_price"),
            total=data.get("total"),
            status=data.get("status"),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert Invoice to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "certificates_count": self.certificates_count,
            "unit_price": float(self.unit_price) if self.unit_price else None,
            "total": float(self.total) if self.total else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
