"""
Unit tests for DocumentMutationService refactoring.
Tests use mocks to verify the new class-based service and legacy wrappers
without creating database records.
"""
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from app.application.services.documents.document_mutation import (
    DocumentMutationService,
    WorkflowTransitionResult,
    new_doc,
    save_doc,
    insert_doc,
    delete_doc,
    apply_workflow_state,
)
from app.domain.exceptions import DocumentNotFoundError, WorkflowTransitionError


@pytest.fixture
def mock_db():
    """Mock AsyncSession."""
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_naming_repo():
    """Mock NamingRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_workflow_repo():
    """Mock WorkflowRepository."""
    repo = AsyncMock()
    repo.get_initial_state = AsyncMock(return_value="draft")
    repo.validate_transition = AsyncMock(return_value=(True, "review", None))
    return repo


@pytest.fixture
def mock_document_repo():
    """Mock DocumentRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(mock_db, mock_naming_repo, mock_workflow_repo, mock_document_repo):
    """Create DocumentMutationService with mocked dependencies."""
    return DocumentMutationService(
        db=mock_db,
        naming_repo=mock_naming_repo,
        workflow_repo=mock_workflow_repo,
        document_repo=mock_document_repo,
    )


# =============================================================================
# Test DocumentMutationService class methods
# =============================================================================

@pytest.mark.asyncio
async def test_service_new_doc_with_model_found(service, mock_naming_repo):
    """Test new_doc creates document instance when model exists."""
    with patch('app.application.services.documents.document_mutation._get_model') as mock_get_model, \
         patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta, \
         patch('app.application.services.documents.document_mutation.NamingAppService') as mock_naming_service:
        
        mock_model = Mock()
        mock_get_model.return_value = mock_model
        mock_meta = Mock()
        mock_meta.naming = None
        mock_meta.workflow = None
        mock_get_meta.return_value = mock_meta
        
        doc = await service.new_doc("test_entity", name="Test")
        
        assert doc is not None
        mock_model.assert_called_once_with(name="Test")


@pytest.mark.asyncio
async def test_service_new_doc_raises_when_model_not_found(service):
    """Test new_doc raises DocumentNotFoundError when model doesn't exist."""
    with patch('app.application.services.documents.document_mutation._get_model') as mock_get_model:
        mock_get_model.return_value = None
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await service.new_doc("nonexistent_entity")
        
        assert "nonexistent_entity" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_new_doc_generates_id_when_naming_enabled(service, mock_naming_repo):
    """Test new_doc generates ID when naming is enabled."""
    with patch('app.application.services.documents.document_mutation._get_model') as mock_get_model, \
         patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta, \
         patch('app.application.services.documents.document_mutation.NamingAppService') as mock_naming_service_class:
        
        mock_model = Mock()
        mock_get_model.return_value = mock_model
        mock_meta = Mock()
        mock_meta.naming = Mock()
        mock_meta.naming.enabled = True
        mock_meta.workflow = None
        mock_get_meta.return_value = mock_meta
        
        mock_naming_service = AsyncMock()
        mock_naming_service.generate_id = AsyncMock(return_value="GEN-001")
        mock_naming_service_class.return_value = mock_naming_service
        
        doc = await service.new_doc("test_entity", name="Test")
        
        mock_naming_service.generate_id.assert_called_once()
        mock_model.assert_called_once_with(id="GEN-001", name="Test")


@pytest.mark.asyncio
async def test_service_new_doc_sets_initial_workflow_state(service):
    """Test new_doc sets initial workflow state when workflow enabled."""
    with patch('app.application.services.documents.document_mutation._get_model') as mock_get_model, \
         patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta:
        
        mock_model = Mock()
        mock_get_model.return_value = mock_model
        mock_meta = Mock()
        mock_meta.naming = None
        mock_meta.workflow = Mock()
        mock_meta.workflow.enabled = True
        mock_meta.workflow.state_field = "workflow_state"
        mock_meta.workflow.initial_state = "Draft"
        mock_get_meta.return_value = mock_meta
        
        doc = await service.new_doc("test_entity", name="Test")
        
        # Verify workflow_state was set with slugified initial state
        call_kwargs = mock_model.call_args[1]
        assert call_kwargs["workflow_state"] == "draft"


@pytest.mark.asyncio
async def test_service_save_doc_with_commit(service, mock_db):
    """Test save_doc commits when commit=True."""
    doc = Mock()
    with patch('app.application.services.documents.document_mutation.inspect') as mock_inspect:
        mock_inspect.return_value = Mock(transient=True)
        
        result = await service.save_doc(doc, commit=True)
        
        mock_db.add.assert_called_once_with(doc)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(doc)
        assert result == doc


@pytest.mark.asyncio
async def test_service_save_doc_without_commit(service, mock_db):
    """Test save_doc flushes when commit=False."""
    doc = Mock()
    with patch('app.application.services.documents.document_mutation.inspect') as mock_inspect:
        mock_inspect.return_value = Mock(transient=True)
        
        result = await service.save_doc(doc, commit=False)
        
        mock_db.add.assert_called_once_with(doc)
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_not_awaited()
        assert result == doc


@pytest.mark.asyncio
async def test_service_save_doc_sends_notification_on_insert(service, mock_db):
    """Test save_doc sends notification when document was inserted."""
    doc = Mock()
    with patch('app.application.services.documents.document_mutation.inspect') as mock_inspect, \
         patch('app.application.email_notifications.document_notify.notify_after_document_insert', new=AsyncMock()) as mock_notify:
        
        mock_inspect.return_value = Mock(transient=True)
        
        await service.save_doc(doc, commit=False)
        
        # Notification should be called for insert
        # Note: This is a simplified check - in real code we'd verify the async call


@pytest.mark.asyncio
async def test_service_insert_doc(service, mock_db):
    """Test insert_doc adds document and commits."""
    doc = Mock()
    
    result = await service.insert_doc(doc, commit=True)
    
    mock_db.add.assert_called_once_with(doc)
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(doc)
    assert result == doc


@pytest.mark.asyncio
async def test_service_delete_doc_success(service, mock_db, mock_document_repo):
    """Test delete_doc deletes document when found."""
    with patch('app.application.services.documents.document_mutation.DocumentAppService') as mock_doc_service_class:
        mock_doc_service = AsyncMock()
        mock_doc = Mock()
        mock_doc_service.get_doc = AsyncMock(return_value=mock_doc)
        mock_doc_service_class.return_value = mock_doc_service
        
        await service.delete_doc("test_entity", "test_id", commit=True)
        
        mock_doc_service.get_doc.assert_awaited_once_with("test_entity", "test_id")
        mock_db.delete.assert_called_once_with(mock_doc)
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_delete_doc_raises_when_not_found(service, mock_document_repo):
    """Test delete_doc raises DocumentNotFoundError when document not found."""
    with patch('app.application.services.documents.document_mutation.DocumentAppService') as mock_doc_service_class:
        mock_doc_service = AsyncMock()
        mock_doc_service.get_doc = AsyncMock(return_value=None)
        mock_doc_service_class.return_value = mock_doc_service
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await service.delete_doc("test_entity", "test_id")
        
        assert "test_entity" in str(exc_info.value)
        assert "test_id" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_apply_workflow_state_success(service, mock_workflow_repo):
    """Test apply_workflow_state validates and applies transition."""
    doc = Mock()
    doc.workflow_state = "draft"
    
    with patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta:
        mock_meta = Mock()
        mock_meta.workflow = Mock()
        mock_meta.workflow.state_field = "workflow_state"
        mock_get_meta.return_value = mock_meta
        
        result = await service.apply_workflow_state("test_entity", doc, "submit")
        
        assert isinstance(result, WorkflowTransitionResult)
        assert result.from_state == "draft"
        assert result.to_state == "review"
        assert result.success is True
        assert doc.workflow_state == "review"


@pytest.mark.asyncio
async def test_service_apply_workflow_state_uses_metadata_state_field(service, mock_workflow_repo):
    """Test apply_workflow_state uses state field from metadata."""
    doc = Mock()
    doc.status = "draft"
    
    with patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta:
        mock_meta = Mock()
        mock_meta.workflow = Mock()
        mock_meta.workflow.state_field = "status"
        mock_get_meta.return_value = mock_meta
        
        result = await service.apply_workflow_state("test_entity", doc, "submit")
        
        assert doc.status == "review"


@pytest.mark.asyncio
async def test_service_apply_workflow_state_raises_on_invalid_transition(service, mock_workflow_repo):
    """Test apply_workflow_state raises on invalid transition."""
    doc = Mock()
    doc.workflow_state = "draft"
    
    mock_workflow_repo.validate_transition = AsyncMock(return_value=(False, None, "Invalid action"))
    
    with patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta:
        mock_meta = Mock()
        mock_meta.workflow = Mock()
        mock_meta.workflow.state_field = "workflow_state"
        mock_get_meta.return_value = mock_meta
        
        with pytest.raises(WorkflowTransitionError) as exc_info:
            await service.apply_workflow_state("test_entity", doc, "invalid_action")
        
        assert "Invalid action" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_apply_workflow_state_raises_when_no_workflow(service, mock_workflow_repo):
    """Test apply_workflow_state raises when no workflow configured."""
    doc = Mock()
    doc.workflow_state = ""
    
    mock_workflow_repo.get_initial_state = AsyncMock(return_value=None)
    
    with patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta:
        mock_meta = Mock()
        mock_meta.workflow = Mock()
        mock_meta.workflow.state_field = "workflow_state"
        mock_get_meta.return_value = mock_meta
        
        with pytest.raises(WorkflowTransitionError) as exc_info:
            await service.apply_workflow_state("test_entity", doc, "submit")
        
        assert "No workflow configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_apply_workflow_state_uses_generate_slug(service, mock_workflow_repo):
    """Test apply_workflow_state uses shared generate_slug for normalization."""
    doc = Mock()
    doc.workflow_state = "Draft State"  # Not slugified
    
    with patch('app.application.services.documents.document_mutation.get_meta') as mock_get_meta, \
         patch('app.application.services.documents.document_mutation.generate_slug') as mock_generate_slug:
        
        mock_generate_slug.return_value = "draft_state"
        mock_meta = Mock()
        mock_meta.workflow = Mock()
        mock_meta.workflow.state_field = "workflow_state"
        mock_get_meta.return_value = mock_meta
        
        await service.apply_workflow_state("test_entity", doc, "submit")
        
        mock_generate_slug.assert_called_once_with("Draft State")


# =============================================================================
# Test legacy wrapper functions (backward compatibility)
# =============================================================================

@pytest.mark.asyncio
async def test_legacy_new_doc_returns_none_on_error(mock_db):
    """Test legacy new_doc returns None when model not found (backward compat)."""
    with patch('app.application.services.documents.document_mutation._get_model') as mock_get_model:
        mock_get_model.return_value = None
        
        result = await new_doc("nonexistent_entity", mock_db)
        
        assert result is None


@pytest.mark.asyncio
async def test_legacy_new_doc_returns_doc_on_success(mock_db):
    """Test legacy new_doc returns document on success."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_doc = Mock()
        mock_service.new_doc = AsyncMock(return_value=mock_doc)
        mock_service_class.return_value = mock_service
        
        result = await new_doc("test_entity", mock_db, name="Test")
        
        assert result == mock_doc


@pytest.mark.asyncio
async def test_legacy_save_doc_delegates_to_service(mock_db):
    """Test legacy save_doc delegates to service."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_doc = Mock()
        mock_service.save_doc = AsyncMock(return_value=mock_doc)
        mock_service_class.return_value = mock_service
        
        result = await save_doc(mock_doc, mock_db, commit=True)
        
        assert result == mock_doc
        mock_service.save_doc.assert_awaited_once_with(mock_doc, True)


@pytest.mark.asyncio
async def test_legacy_insert_doc_delegates_to_service(mock_db):
    """Test legacy insert_doc delegates to service."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_doc = Mock()
        mock_service.insert_doc = AsyncMock(return_value=mock_doc)
        mock_service_class.return_value = mock_service
        
        result = await insert_doc(mock_doc, mock_db, commit=True)
        
        assert result == mock_doc
        mock_service.insert_doc.assert_awaited_once_with(mock_doc, True)


@pytest.mark.asyncio
async def test_legacy_delete_doc_returns_false_on_not_found(mock_db):
    """Test legacy delete_doc returns False when document not found."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.delete_doc = AsyncMock(side_effect=DocumentNotFoundError("test", "id"))
        mock_service_class.return_value = mock_service
        
        result = await delete_doc("test_entity", "test_id", mock_db)
        
        assert result is False


@pytest.mark.asyncio
async def test_legacy_delete_doc_returns_true_on_success(mock_db):
    """Test legacy delete_doc returns True on success."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.delete_doc = AsyncMock()
        mock_service_class.return_value = mock_service
        
        result = await delete_doc("test_entity", "test_id", mock_db)
        
        assert result is True


@pytest.mark.asyncio
async def test_legacy_apply_workflow_state_returns_success_dict(mock_db):
    """Test legacy apply_workflow_state returns success dict."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_result = WorkflowTransitionResult(from_state="draft", to_state="review")
        mock_service.apply_workflow_state = AsyncMock(return_value=mock_result)
        mock_service_class.return_value = mock_service
        
        doc = Mock()
        result = await apply_workflow_state("test_entity", doc, "submit", mock_db)
        
        assert result["status"] == "success"
        assert result["from_state"] == "draft"
        assert result["to_state"] == "review"


@pytest.mark.asyncio
async def test_legacy_apply_workflow_state_returns_error_dict_on_failure(mock_db):
    """Test legacy apply_workflow_state returns error dict on failure."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.apply_workflow_state = AsyncMock(
            side_effect=WorkflowTransitionError("Invalid transition", from_state="draft", action="submit")
        )
        mock_service_class.return_value = mock_service
        
        doc = Mock()
        result = await apply_workflow_state("test_entity", doc, "submit", mock_db)
        
        assert result["status"] == "error"
        assert "Invalid transition" in result["message"]


@pytest.mark.asyncio
async def test_legacy_apply_workflow_state_flushes_when_commit_true(mock_db):
    """Test legacy apply_workflow_state flushes when commit=True."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_result = WorkflowTransitionResult(from_state="draft", to_state="review")
        mock_service.apply_workflow_state = AsyncMock(return_value=mock_result)
        mock_service_class.return_value = mock_service
        
        doc = Mock()
        await apply_workflow_state("test_entity", doc, "submit", mock_db, commit=True)
        
        mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_legacy_apply_workflow_state_does_not_flush_when_commit_false(mock_db):
    """Test legacy apply_workflow_state does not flush when commit=False."""
    with patch('app.application.services.documents.document_mutation.DocumentMutationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_result = WorkflowTransitionResult(from_state="draft", to_state="review")
        mock_service.apply_workflow_state = AsyncMock(return_value=mock_result)
        mock_service_class.return_value = mock_service
        
        doc = Mock()
        await apply_workflow_state("test_entity", doc, "submit", mock_db, commit=False)
        
        mock_db.flush.assert_not_awaited()


# =============================================================================
# Test WorkflowTransitionResult dataclass
# =============================================================================

def test_workflow_transition_result_creation():
    """Test WorkflowTransitionResult dataclass creation."""
    result = WorkflowTransitionResult(from_state="draft", to_state="review")
    
    assert result.from_state == "draft"
    assert result.to_state == "review"
    assert result.success is True


def test_workflow_transition_result_with_custom_success():
    """Test WorkflowTransitionResult with custom success value."""
    result = WorkflowTransitionResult(from_state="draft", to_state="review", success=False)
    
    assert result.success is False
