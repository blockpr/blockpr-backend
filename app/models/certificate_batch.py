from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CertificateBatch:
    id: UUID
    status: str
    certificates_count: Optional[int]
    merkle_root: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    @classmethod
    def from_dict(cls, data: dict) -> "CertificateBatch":
        """Create CertificateBatch from database row"""
        return cls(
            id=data["id"],
            status=data.get("status", "pending"),
            certificates_count=data.get("certificates_count"),
            merkle_root=data.get("merkle_root"),
            created_at=data["created_at"],
            processed_at=data.get("processed_at"),
        )

    def to_dict(self) -> dict:
        """Convert CertificateBatch to dictionary"""
        return {
            "id": str(self.id),
            "status": self.status,
            "certificates_count": self.certificates_count,
            "merkle_root": self.merkle_root,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
