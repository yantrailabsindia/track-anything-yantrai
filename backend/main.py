from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routers import activity, screenshots, stats, auth_router, download, telemetry, teams, organizations, invites, chat, chatrooms, cctv
from backend.auth import init_default_users
from backend.database import engine
from backend.models import Base
from pathlib import Path

app = FastAPI(title="ProMe API")

# CORS for local development (allowing any origin for network access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for screenshots
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

CCTV_DIR = DATA_DIR / "cctv"
CCTV_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/cctv-data", StaticFiles(directory=str(CCTV_DIR)), name="cctv-data")

# Include routers
# Note: In backend.routers.__init__, we exported them aliased directly, e.g. 'router as auth_router'
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(activity, prefix="/api/activity", tags=["activity"])
app.include_router(screenshots, prefix="/api/screenshots", tags=["screenshots"])
app.include_router(stats, prefix="/api/stats", tags=["stats"])
app.include_router(download, prefix="/api/download", tags=["download"])
app.include_router(telemetry, prefix="/api/telemetry", tags=["telemetry"])
app.include_router(teams, prefix="/api/teams", tags=["teams"])
app.include_router(organizations, prefix="/api/orgs", tags=["organizations"])
app.include_router(invites, prefix="/api/invites", tags=["invites"])
app.include_router(chat, prefix="/api/chat", tags=["chat"])
app.include_router(chatrooms, prefix="/api/chatrooms", tags=["chatrooms"])
app.include_router(cctv, prefix="/api/cctv", tags=["cctv"])

@app.get("/")
def read_root():
    return {"status": "ProMe API is running"}

# Initialize DB tables and default admin account on startup
# metadata.create_all handles new tables, init_default_users ensures org/super_admin exist
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    init_default_users()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
