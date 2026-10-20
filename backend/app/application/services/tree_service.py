"""
Tree service for managing hierarchical data.
"""
from typing import List, Dict, Any, Optional

from app.domain.protocols.tree import TreeRepositoryProtocol
from app.meta.registry import MetaRegistry


class TreeService:
    """Service for tree operations."""
    
    def __init__(self, tree_repository: TreeRepositoryProtocol):
        self.tree_repository = tree_repository
    
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
        """Get tree data for an entity."""
        
        # Validate entity exists and is a tree
        entity_meta = MetaRegistry.get(entity_name)
        if not entity_meta:
            raise ValueError(f"Entity {entity_name} not found")
        
        if not entity_meta.is_tree:
            raise ValueError(f"Entity {entity_name} is not configured as a tree")
        
        # Get tree data
        return await self.tree_repository.get_tree_data(
            entity_name=entity_name,
            parent_field=parent_field,
            title_field=title_field,
            row_scope_service=row_scope_service,
            user_id=user_id,
            role_ids=role_ids,
            role_names=role_names,
            is_superuser=is_superuser,
        )
