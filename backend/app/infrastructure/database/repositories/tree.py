"""
Tree repository implementation.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.protocols.tree import TreeRepositoryProtocol
from app.meta.registry import MetaRegistry
from app.infrastructure.database.repositories.entity_repository import get_entity_model


class TreeRepository(TreeRepositoryProtocol):
    """SQLAlchemy implementation of tree repository."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tree_data(
        self,
        entity_name: str,
        parent_field: Optional[str] = None,
        title_field: Optional[str] = None,
        row_scope_service: Optional[Any] = None,
        user_id: Optional[str] = None,
        role_ids: Optional[list[str]] = None,
        role_names: Optional[list[str]] = None,
        is_superuser: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get all records for tree structure with minimal fields."""
        
        # Get entity metadata
        entity_meta = MetaRegistry.get(entity_name)
        if not entity_meta:
            raise ValueError(f"Entity {entity_name} not found")
        
        model = get_entity_model(entity_name)
        if not model:
            raise ValueError(f"Model for {entity_name} not found")
        
        # Determine fields to select
        fields_to_select = ["id"]
        
        # Add parent field
        if parent_field:
            fields_to_select.append(parent_field)
        elif entity_meta.tree_parent_field:
            fields_to_select.append(entity_meta.tree_parent_field)
        else:
            # Try to find a parent field heuristically
            for field_name, field_meta in entity_meta.fields.items():
                if field_meta.field_type == "Link" and field_meta.options == entity_name:
                    fields_to_select.append(field_name)
                    break
        
        # Add title field
        if title_field:
            fields_to_select.append(title_field)
        elif entity_meta.title_field:
            fields_to_select.append(entity_meta.title_field)
        else:
            fields_to_select.append("name")  # Default fallback
        
        # Build ORM query
        columns = [getattr(model, f) for f in fields_to_select if hasattr(model, f)]
        query = select(*columns)
        
        # Apply row scope if provided
        if row_scope_service:
            query = await row_scope_service.apply_scope_to_query(
                query,
                model,
                entity_name,
                user_id or "",
                role_ids or [],
                role_names or [],
                is_superuser,
            )
        
        # Order by title field
        title_col = getattr(model, fields_to_select[-1], None)
        if title_col is not None:
            query = query.order_by(title_col)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        # Convert to list of dicts
        data = []
        for row in rows:
            row_dict = {}
            for i, field in enumerate(fields_to_select):
                row_dict[field] = row[i]
            data.append(row_dict)
        
        return data
