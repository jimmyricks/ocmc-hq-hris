"""
Print Assembler Loader
=======================
Auto-registers all entity-specific print data assemblers.

Previously registered EAM assemblers (purchase_order, purchase_request, work_order,
incident).  This is now a placeholder so the print service can load future
assemblers without requiring code changes elsewhere.
"""

_loaded = False


def load_print_assemblers() -> None:
    """Register all known print data assemblers. Idempotent."""
    global _loaded
    if _loaded:
        return
    # Future assemblers are registered here
    _loaded = True
