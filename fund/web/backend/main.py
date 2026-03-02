from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST_DIR, get_db
from .routers import ranking, advanced_ranking, products, portfolio, transactions, risk_levels

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ranking.router)
app.include_router(advanced_ranking.router)
app.include_router(products.router)
app.include_router(portfolio.router)
app.include_router(transactions.router)
app.include_router(risk_levels.router)

dist_dir = Path(FRONTEND_DIST_DIR)
assets_dir = dist_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not Found")
    index_file = dist_dir / "index.html"
    candidate = dist_dir / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    if index_file.exists():
        return FileResponse(index_file)
    return {"detail": "Frontend not built"}

@app.on_event("startup")
def startup():
    pass

@app.on_event("shutdown")
def shutdown():
    pass
