"""Standalone Arial API service.

Runs arial_api on its own uvicorn (port 8003) so SailingSA api.py redeploys can
never drop the /api/arial routes. nginx routes /api/arial/ here.
"""
from fastapi import FastAPI

from arial_api import router as arial_router

app = FastAPI(title="Arial API", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(arial_router)


@app.get("/api/arial/_health")
def health() -> dict[str, bool]:
    return {"ok": True}
