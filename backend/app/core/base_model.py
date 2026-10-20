"""
Core Layer: Base ORM Model

Common audit columns (id, created_by, created_at, modified_by, modified_at)
for all entities.

Clean Architecture Layer: Core
Responsibility: Provide base model with common fields for all entities
"""
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class BaseModel(Base):
    """
    Abstract base model with common audit fields.
    
    All entities inherit from this to get:
    - id: Human-readable naming code (e.g., AST-0001) - set by NamingService
    - created_by: Actor who created the record
    - created_at: Auto-set on insert
    - last_modified_by: Actor who last modified the record (modified_by concept)
    - updated_at: Auto-updated on every change (modified_at concept)
    
    Note: id is NOT auto-generated here. It must be set by NamingService
    before insert based on the entity's naming configuration.
    """
    __abstract__ = True
    
    # ID is the naming code (e.g., AST-0001), NOT a UUID
    # Must be set before insert by NamingService
    id: Mapped[str] = mapped_column(
        String(50), 
        primary_key=True
    )
    
    created_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    
    last_modified_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
