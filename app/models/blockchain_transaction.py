from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class BlockchainTransaction:
    id: UUID
    batch_id: UUID
    blockchain: Optional[str]
    network: Optional[str]
    tx_hash: Optional[str]
    block_number: Optional[int]
    explorer_url: Optional[str]
    status: Optional[str]
    created_at: datetime
    confirmed_at: Optional[datetime]

    @classmethod
    def from_dict(cls, data: dict) -> "BlockchainTransaction":
        """Create BlockchainTransaction from database row"""
        return cls(
            id=data["id"],
            batch_id=data["batch_id"],
            blockchain=data.get("blockchain"),
            network=data.get("network"),
            tx_hash=data.get("tx_hash"),
            block_number=data.get("block_number"),
            explorer_url=data.get("explorer_url"),
            status=data.get("status"),
            created_at=data["created_at"],
            confirmed_at=data.get("confirmed_at"),
        )

    def to_dict(self) -> dict:
        """Convert BlockchainTransaction to dictionary"""
        return {
            "id": str(self.id),
            "batch_id": str(self.batch_id),
            "blockchain": self.blockchain,
            "network": self.network,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "explorer_url": self.explorer_url,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
