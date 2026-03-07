from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass
class Certificate:
    id: UUID
    user_id: UUID
    external_id: Optional[str]
    certificate_type: Optional[str]
    document_hash: str
    metadata: Optional[Dict[str, Any]]
    batch_id: Optional[UUID]
    merkle_proof: Optional[Dict[str, Any]]
    blockchain_tx_id: Optional[UUID]
    verification_url: Optional[str]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Certificate":
        """Create Certificate from database row"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            external_id=data.get("external_id"),
            certificate_type=data.get("certificate_type"),
            document_hash=data["document_hash"],
            metadata=data.get("metadata"),
            batch_id=data.get("batch_id"),
            merkle_proof=data.get("merkle_proof"),
            blockchain_tx_id=data.get("blockchain_tx_id"),
            verification_url=data.get("verification_url"),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Convert Certificate to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "external_id": self.external_id,
            "certificate_type": self.certificate_type,
            "document_hash": self.document_hash,
            "metadata": self.metadata,
            "batch_id": str(self.batch_id) if self.batch_id else None,
            "merkle_proof": self.merkle_proof,
            "blockchain_tx_id": str(self.blockchain_tx_id) if self.blockchain_tx_id else None,
            "verification_url": self.verification_url,
            "created_at": self.created_at.isoformat(),
        }
