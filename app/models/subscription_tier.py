from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class SubscriptionTier:
    id: UUID
    name: str
    price_monthly: Optional[Decimal]
    price_per_certificate: Optional[Decimal]
    included_certificates: Optional[int]
    max_certificates: Optional[int]
    api_access: bool
    priority_support: bool
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "SubscriptionTier":
        """Create SubscriptionTier from database row"""
        return cls(
            id=data["id"],
            name=data["name"],
            price_monthly=data.get("price_monthly"),
            price_per_certificate=data.get("price_per_certificate"),
            included_certificates=data.get("included_certificates"),
            max_certificates=data.get("max_certificates"),
            api_access=data.get("api_access", True),
            priority_support=data.get("priority_support", False),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert SubscriptionTier to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "price_monthly": float(self.price_monthly) if self.price_monthly else None,
            "price_per_certificate": float(self.price_per_certificate) if self.price_per_certificate else None,
            "included_certificates": self.included_certificates,
            "max_certificates": self.max_certificates,
            "api_access": self.api_access,
            "priority_support": self.priority_support,
            "created_at": self.created_at.isoformat(),
        }
