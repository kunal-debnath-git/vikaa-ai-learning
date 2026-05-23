from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.routers import sessions, questions, analytics, users, duk

app = FastAPI(
    title="Advanced Interview Prep System",
    description="Leadership-level interview preparation for Data, Cloud & GenAI roles",
    version="1.0.5",
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.5"}

# CORS — wildcard without credentials is valid for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(duk.router, prefix="/api")

# Static frontend
frontend_path = Path(__file__).parent / "frontend"

if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))
