from typing import Any, Optional
from pydantic import BaseModel, model_validator


class ActionRequest(BaseModel):
    action: str  # create, update, delete, or custom action
    data: Optional[dict[str, Any]] = None
    id: Optional[str] = None
    children: Optional[dict[str, dict[str, Any]]] = None  # { child_entity: { rows: [], deleted_ids: [] } }


class ActionResponse(BaseModel):
    status: str  # success, error
    message: str
    data: Optional[Any] = None
    errors: Optional[dict[str, str]] = None


class WorkflowRequest(BaseModel):
    action: str  # workflow action name
    id: Optional[str] = None
    record_id: Optional[str] = None

    @model_validator(mode="after")
    def require_record_identifier(self):
        if not self.id and not self.record_id:
            raise ValueError("id or record_id is required")
        return self


class ListResponse(BaseModel):
    status: str
    data: list[Any]
    total: int
    page: int
    page_size: int
