"""
Report Interfaces
=================

Protocol and interface definitions for the report generator.

Expected provider interface:
    class ReportDataProvider(Protocol):
        async def fetch(self, filters: dict, db: AsyncSession) -> dict: ...

Future implementations can reintroduce typed protocols here.
"""
