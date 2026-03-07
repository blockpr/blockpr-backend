from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class User:
    id: UUID
    company_name: str
    tax_id: Optional[str]
    email: str
    password_hash: str
    contact_name: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    email_verified: bool
    email_verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from database row"""
        return cls(
            id=data["id"],
            company_name=data["company_name"],
            tax_id=data.get("tax_id"),
            email=data["email"],
            password_hash=data["password_hash"],
            contact_name=data.get("contact_name"),
            contact_phone=data.get("contact_phone"),
            address=data.get("address"),
            city=data.get("city"),
            country=data.get("country"),
            email_verified=data.get("email_verified", False),
            email_verified_at=data.get("email_verified_at"),
            last_login_at=data.get("last_login_at"),
            is_active=data.get("is_active", True),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def to_dict(self) -> dict:
        """Convert User to dictionary"""
        return {
            "id": str(self.id),
            "company_name": self.company_name,
            "tax_id": self.tax_id,
            "email": self.email,
            "password_hash": self.password_hash,
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "address": self.address,
            "city": self.city,
            "country": self.country,
            "email_verified": self.email_verified,
            "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
