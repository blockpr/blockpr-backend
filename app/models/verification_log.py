from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class VerificationLog:
    id: UUID
    certificate_id: UUID
    verified: Optional[bool]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "VerificationLog":
        """Create VerificationLog from database row"""
        return cls(
            id=data["id"],
            certificate_id=data["certificate_id"],
            verified=data.get("verified"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert VerificationLog to dictionary"""
        return {
            "id": str(self.id),
            "certificate_id": str(self.certificate_id),
            "verified": self.verified,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
        }
