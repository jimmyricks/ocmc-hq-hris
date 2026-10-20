# Service Migration Tracker

| Phase | Service             | Old Location                               | New Location                                        | Status    | Files Updated | Date |
| ----- | ------------------- | ------------------------------------------ | --------------------------------------------------- | --------- | ------------- | ---- |
| 1     | error_logger        | app/services/error_logger.py               | application/services/integrations/error_logger.py   | Completed | 1             |      |
| 1     | audit               | app/services/audit.py                      | application/services/integrations/audit.py          | Completed | 0             |      |
| 1     | query_link_handlers | app/services/query_link_handlers.py        | application/services/documents/query_link.py        | Completed | 4             |      |
| 1     | print_service       | app/services/print_service.py              | application/services/documents/print.py             | Completed | 2             |      |
| 2     | naming              | app/services/naming.py                     | application/services/documents/naming.py            | Completed | 6             |      |
| 2     | scheduler           | app/services/scheduler.py                  | application/services/scheduling/scheduler.py        | Completed | 1             |      |
| 2     | server_actions      | app/services/server_actions.py             | application/services/documents/server_actions.py    | Completed | 9             |      |
| 3     | document            | app/services/document.py                   | application/services/documents/document.py          | Completed | 40+           |      |
| 3     | document_query      | app/services/document_query.py             | application/services/documents/document_query.py    | Completed | 40+           |      |
| 3     | document_mutation   | app/services/document_mutation.py          | application/services/documents/document_mutation.py | Completed | 8             |      |
| 4     | socketio_manager    | app/services/socketio_manager.py           | application/services/notifications/socketio.py      | Completed | 8             |      |
| 4     | workflow            | app/services/workflow.py                   | application/services/workflows/workflow.py          | Completed | 10            |      |
| 5     | rbac                | app/services/rbac.py                       | application/services/access_control/rbac.py         | Completed | 16            |      |
| 6     | import_export       | app/services/import_export.py              | application/services/integrations/import_export.py  | Completed | 2             |      |
| 8     | workflow_rename     | application/services/workflows/workflow.py | application/services/workflows/workflow_db.py       | Pending   | 10            |      |
