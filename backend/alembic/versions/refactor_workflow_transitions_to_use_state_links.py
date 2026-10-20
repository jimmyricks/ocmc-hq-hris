"""Refactor workflow transitions to use state links instead of direct state references

This migration fixes a data integrity issue where transitions could reference states
not linked to the workflow. Now transitions reference WorkflowStateLink instead of
WorkflowState directly, ensuring transitions only exist between states that belong
to the same workflow.

Additionally removes the redundant workflow_id column since the workflow can be
determined from the state links, makes the link IDs non-nullable to ensure
data integrity, and makes Workflow.name and target_entity non-nullable.

Revision ID: refactor_workflow_transitions_to_use_state_links
Revises: 0059_add_pm_generation_ledger
Create Date: 2026-07-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'refactor_transitions_links'
down_revision = '0059_add_pm_generation_ledger'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get database session
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        # Step 1: Add new columns as nullable
        op.add_column('core_workflow_transitions', 
                     sa.Column('from_state_link_id', sa.String(36), nullable=True))
        op.add_column('core_workflow_transitions', 
                     sa.Column('to_state_link_id', sa.String(36), nullable=True))
        
        # Step 2: Migrate existing data
        # For each transition, find the corresponding state link IDs
        migrate_sql = text("""
            UPDATE core_workflow_transitions t
            SET from_state_link_id = (
                SELECT id FROM core_workflow_state_links l
                WHERE l.workflow_id = t.workflow_id AND l.state_id = t.from_state_id
                LIMIT 1
            ),
            to_state_link_id = (
                SELECT id FROM core_workflow_state_links l
                WHERE l.workflow_id = t.workflow_id AND l.state_id = t.to_state_id
                LIMIT 1
            )
            WHERE t.from_state_id IS NOT NULL OR t.to_state_id IS NOT NULL
        """)
        session.execute(migrate_sql)
        session.commit()
        
        # Step 3: Add foreign key constraints
        op.create_foreign_key(
            'fk_workflow_transitions_from_state_link',
            'core_workflow_transitions', 'core_workflow_state_links',
            ['from_state_link_id'], ['id']
        )
        op.create_foreign_key(
            'fk_workflow_transitions_to_state_link',
            'core_workflow_transitions', 'core_workflow_state_links',
            ['to_state_link_id'], ['id']
        )
        
        # Step 4: Drop old columns and their foreign key constraints
        # The old foreign keys will be automatically dropped when we drop the columns
        op.drop_column('core_workflow_transitions', 'from_state_id')
        op.drop_column('core_workflow_transitions', 'to_state_id')
        
        # Step 5: Drop the redundant workflow_id column
        op.drop_column('core_workflow_transitions', 'workflow_id')
        
        # Step 6: Make the new link columns non-nullable
        op.alter_column('core_workflow_transitions', 'from_state_link_id', nullable=False)
        op.alter_column('core_workflow_transitions', 'to_state_link_id', nullable=False)
        
        # Step 7: Make Workflow.name and target_entity non-nullable
        # First update any NULL values to defaults
        update_workflow_sql = text("""
            UPDATE core_workflows
            SET name = COALESCE(name, 'Unnamed Workflow'),
                target_entity = COALESCE(target_entity, 'unknown')
            WHERE name IS NULL OR target_entity IS NULL
        """)
        session.execute(update_workflow_sql)
        session.commit()
        
        op.alter_column('core_workflows', 'name', nullable=False)
        op.alter_column('core_workflows', 'target_entity', nullable=False)
        
    finally:
        session.close()


def downgrade() -> None:
    # Get database session
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        # Step 1: Make Workflow.name and target_entity nullable again
        op.alter_column('core_workflows', 'name', nullable=True)
        op.alter_column('core_workflows', 'target_entity', nullable=True)
        
        # Step 2: Make link columns nullable again for migration
        op.alter_column('core_workflow_transitions', 'from_state_link_id', nullable=True)
        op.alter_column('core_workflow_transitions', 'to_state_link_id', nullable=True)
        
        # Step 3: Add back workflow_id column
        op.add_column('core_workflow_transitions', 
                     sa.Column('workflow_id', sa.String(36), nullable=True))
        
        # Step 4: Add back old columns as nullable
        op.add_column('core_workflow_transitions', 
                     sa.Column('from_state_id', sa.String(36), nullable=True))
        op.add_column('core_workflow_transitions', 
                     sa.Column('to_state_id', sa.String(36), nullable=True))
        
        # Step 5: Migrate data back from state links to states
        # Also restore workflow_id from the state links
        migrate_back_sql = text("""
            UPDATE core_workflow_transitions t
            SET from_state_id = (
                SELECT l.state_id FROM core_workflow_state_links l
                WHERE l.id = t.from_state_link_id
                LIMIT 1
            ),
            to_state_id = (
                SELECT l.state_id FROM core_workflow_state_links l
                WHERE l.id = t.to_state_link_id
                LIMIT 1
            ),
            workflow_id = (
                SELECT l.workflow_id FROM core_workflow_state_links l
                WHERE l.id = t.from_state_link_id
                LIMIT 1
            )
            WHERE t.from_state_link_id IS NOT NULL OR t.to_state_link_id IS NOT NULL
        """)
        session.execute(migrate_back_sql)
        session.commit()
        
        # Step 6: Add back old foreign key constraints
        op.create_foreign_key(
            'fk_workflow_transitions_from_state',
            'core_workflow_transitions', 'core_workflow_states',
            ['from_state_id'], ['id']
        )
        op.create_foreign_key(
            'fk_workflow_transitions_to_state',
            'core_workflow_transitions', 'core_workflow_states',
            ['to_state_id'], ['id']
        )
        op.create_foreign_key(
            'fk_workflow_transitions_workflow',
            'core_workflow_transitions', 'core_workflows',
            ['workflow_id'], ['id']
        )
        
        # Step 7: Drop new columns and their foreign key constraints
        op.drop_constraint('fk_workflow_transitions_from_state_link', 'core_workflow_transitions', type_='foreignkey')
        op.drop_constraint('fk_workflow_transitions_to_state_link', 'core_workflow_transitions', type_='foreignkey')
        op.drop_column('core_workflow_transitions', 'from_state_link_id')
        op.drop_column('core_workflow_transitions', 'to_state_link_id')
        
    finally:
        session.close()
