from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import portfolio, products, ranking, risk_levels

app = FastAPI(
    title="BOC Fund NAV Dashboard",
    description="中国银行代销理财产品净值数据看板 API",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS – 开发模式允许 Vite dev server (localhost:5173)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
app.include_router(ranking.router)
app.include_router(portfolio.router)
app.include_router(products.router)
app.include_router(risk_levels.router)


# ---------------------------------------------------------------------------
# 生产模式：托管前端静态文件
# ---------------------------------------------------------------------------
from .config import FRONTEND_DIST_DIR

_dist = Path(FRONTEND_DIST_DIR)
if _dist.is_dir():
    # SPA fallback: serve index.html for any non-API route
    from fastapi.responses import FileResponse

    @app.get("/")
    async def serve_index():
        return FileResponse(str(_dist / "index.html"))

    # 静态资源
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    # SPA catch-all (must be last)
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = _dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_dist / "index.html"))
