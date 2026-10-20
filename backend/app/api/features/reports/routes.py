"""
Reports Router
==============

Serves report definitions, generates HTML previews, and produces PDF downloads.

Previously implemented endpoints:
  GET  /reports              → list available reports
  GET  /reports/{key}        → report metadata
  POST /reports/{key}/generate → HTML preview
  POST /reports/{key}/pdf    → PDF download
  POST /reports/{key}/xlsx   → Excel download

In the barebones backend the router is empty; the reports registry can be
populated to re-enable these endpoints.
"""
from fastapi import APIRouter

router = APIRouter(tags=["reports"])
