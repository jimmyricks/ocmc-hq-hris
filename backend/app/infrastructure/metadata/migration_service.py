"""
Migration Service
=================
Handles database migration generation and execution using Alembic.
Provides safe migration categorization and rollback capabilities.

Performance note: read-only operations (current revision, migration history,
head revision) use direct DB queries and the Alembic ScriptDirectory Python API
instead of subprocess calls. This avoids spawning a new Python interpreter that
must re-import all 129 entity models for each query. Only write operations
(generate, apply, rollback) and schema-diff checks still use subprocesses.
"""
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import re

from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings


class MigrationService:
    """Service for managing database migrations."""
    
    def __init__(self):
        self.app_dir = Path(__file__).parent.parent.parent  # infrastructure/metadata/ → app/
        self.backend_dir = self.app_dir.parent
        self.alembic_dir = self.backend_dir / "alembic"
        self.versions_dir = self.alembic_dir / "versions"
        self._alembic_config: Optional[Config] = None
        self._script_dir: Optional[ScriptDirectory] = None
        self._sync_engine = None

    # ------------------------------------------------------------------
    # Internal helpers (cached)
    # ------------------------------------------------------------------

    def _get_alembic_config(self) -> Config:
        """Build and cache an Alembic Config object."""
        if self._alembic_config is None:
            cfg = Config(str(self.backend_dir / "alembic.ini"))
            cfg.set_main_option("script_location", str(self.alembic_dir))
            cfg.set_main_option("sqlalchemy.url", settings.sync_database_url)
            self._alembic_config = cfg
        return self._alembic_config

    def _get_script_dir(self) -> ScriptDirectory:
        """Build and cache a ScriptDirectory for filesystem-only migration queries."""
        if self._script_dir is None:
            self._script_dir = ScriptDirectory.from_config(self._get_alembic_config())
        return self._script_dir

    def _get_sync_engine(self):
        """Lazily create a sync engine for direct DB queries (e.g. alembic_version)."""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                settings.sync_database_url,
                pool_pre_ping=True,
            )
        return self._sync_engine
    
    def generate_migration(self, message: str, autogenerate: bool = True, auto_upgrade: bool = True) -> dict:
        """Generate a new Alembic migration.
        
        Args:
            message: Migration message/description
            autogenerate: Whether to auto-detect model changes
            auto_upgrade: If True, automatically apply pending migrations first
        """
        try:
            # First check if database is up to date
            if auto_upgrade:
                current_result = self.get_current_revision()
                head_result = self._get_head_revision()
                
                if current_result.get("success") and head_result.get("success"):
                    current = current_result.get("revision", "").strip()
                    head = head_result.get("revision", "").strip()
                    
                    # If not at head, apply pending migrations first
                    if current != head and head:
                        upgrade_result = self.apply_migration("head")
                        if not upgrade_result.get("success"):
                            return {
                                "success": False,
                                "error": f"Failed to apply pending migrations before generating new one: {upgrade_result.get('error')}",
                                "hint": "Apply pending migrations first using the Migrations page"
                            }
            
            cmd = ["alembic", "revision"]
            if autogenerate:
                cmd.append("--autogenerate")
            cmd.extend(["-m", message])
            
            result = subprocess.run(
                cmd,
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Migration generation failed"
                # Provide helpful hint for common errors
                hint = None
                if "Target database is not up to date" in error_msg:
                    hint = "Run 'Apply Migrations' first to sync the database with existing migrations"
                elif "No changes in schema detected" in (result.stdout or ""):
                    return {
                        "success": True,
                        "message": "No schema changes detected - no migration needed",
                        "no_changes": True
                    }
                
                return {
                    "success": False,
                    "error": error_msg,
                    "hint": hint,
                    "stdout": result.stdout
                }
            
            # Check if no changes were detected
            if "No changes in schema detected" in (result.stdout or ""):
                return {
                    "success": True,
                    "message": "No schema changes detected - no migration needed",
                    "no_changes": True
                }
            
            # Extract migration file path from output
            migration_file = self._extract_migration_path(result.stdout)
            
            return {
                "success": True,
                "message": f"Migration generated: {message}",
                "migration_file": migration_file,
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_head_revision(self) -> dict:
        """Get the head revision from migration files (filesystem only, no subprocess)."""
        try:
            script_dir = self._get_script_dir()
            head = script_dir.get_current_head()
            return {
                "success": True,
                "revision": head or "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_migration_path(self, output: str) -> Optional[str]:
        """Extract migration file path from alembic output."""
        # Look for pattern like "Generating /path/to/migration.py"
        match = re.search(r'Generating\s+(.+\.py)', output)
        if match:
            return match.group(1)
        return None
    
    def apply_migration(self, revision: str = "head") -> dict:
        """Apply migrations up to a specific revision."""
        try:
            result = subprocess.run(
                ["alembic", "upgrade", revision],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Migration failed",
                    "stdout": result.stdout
                }
            
            return {
                "success": True,
                "message": f"Migrated to {revision}",
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def rollback_migration(self, steps: int = 1) -> dict:
        """Rollback migrations by a number of steps."""
        try:
            result = subprocess.run(
                ["alembic", "downgrade", f"-{steps}"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Rollback failed",
                    "stdout": result.stdout
                }
            
            return {
                "success": True,
                "message": f"Rolled back {steps} migration(s)",
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_current_revision(self) -> dict:
        """Get the current database revision via direct DB query (no subprocess)."""
        try:
            engine = self._get_sync_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                revision = row[0] if row else None
            return {
                "success": True,
                "revision": revision,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pending_migrations(self, current_revision: Optional[str] = None, limit: int = 5) -> dict:
        """Get migration history with pending status via ScriptDirectory (no subprocess).

        Args:
            current_revision: The current DB revision, if already known.
                If None, a DB query will be made to fetch it.
            limit: Maximum number of recent migrations to return (plus the
                current revision if it falls outside that range).
        """
        try:
            if current_revision is None:
                current_result = self.get_current_revision()
                if not current_result.get("success"):
                    return current_result
                current_revision = current_result.get("revision")

            script_dir = self._get_script_dir()

            # Walk the revision chain from head down to the root
            all_migrations = []
            current_found = False
            current_entry = None

            for revision in script_dir.walk_revisions():
                rev_id = revision.revision
                is_current = (rev_id == current_revision)
                if is_current:
                    current_found = True

                entry = {
                    "revision": rev_id,
                    "parent": revision.down_revision or "None",
                    "message": revision.doc or "",
                    "is_current": is_current,
                    "is_pending": not current_found and not is_current,
                }
                all_migrations.append(entry)
                if is_current:
                    current_entry = entry

            # Keep only the most recent `limit` entries.
            # If the current revision fell outside that window, append it.
            migrations = all_migrations[:limit]
            if current_entry and current_entry not in migrations:
                migrations.append(current_entry)

            return {
                "success": True,
                "migrations": migrations,
                "total_count": len(all_migrations),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_migration_files(self) -> list[dict]:
        """List all migration files."""
        if not self.versions_dir.exists():
            return []
        
        migrations = []
        for file in self.versions_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue
            
            stat = file.stat()
            migrations.append({
                "filename": file.name,
                "path": str(file),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        
        return sorted(migrations, key=lambda x: x["created_at"], reverse=True)
    
    def check_migration_needed(self) -> dict:
        """Check if there are model changes that need migration (in-process, no subprocess)."""
        try:
            import os as _os
            from alembic import command
            from alembic.util.exc import CommandError

            cfg = self._get_alembic_config()

            # Signal env.py to skip fileConfig (avoids alembic INFO log spam)
            _os.environ["IN_PROCESS_ALEMBIC"] = "1"
            try:
                command.check(cfg)
            finally:
                _os.environ.pop("IN_PROCESS_ALEMBIC", None)

            return {
                "success": True,
                "needs_migration": False,
                "message": "No schema changes detected",
            }
        except CommandError as e:
            msg = str(e)
            needs = "No changes in schema detected" not in msg
            return {
                "success": True,
                "needs_migration": needs,
                "message": msg,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def preview_migration(self) -> dict:
        """Preview what changes would be in the next migration."""
        try:
            # Generate migration to temp file, read it, then delete
            result = subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", "preview_temp", "--sql"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            return {
                "success": True,
                "preview": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
