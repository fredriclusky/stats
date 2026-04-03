import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.triggers.interval import IntervalTrigger
from backend.scheduler import scheduler
import os

from backend.database import init_db
from backend.routers import auth, affiliates, campaigns, stats, inbound, outbound, partner, suggestions, schedule, sync
from backend.services.sync_service import sync_all_accounts
from backend.models.user import User
from backend.database import AsyncSessionLocal
from backend.routers.auth import hash_password
from sqlalchemy import select
from backend.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()



async def ensure_admin_user():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_username))
        user = result.scalar_one_or_none()
        if not user:
            admin = User(
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                role="admin"
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Created admin user: {settings.admin_username}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_admin_user()
    scheduler.add_job(
        sync_all_accounts,
        IntervalTrigger(minutes=15),
        id="sync_affiliates",
        replace_existing=True,
        kwargs={"days_back": 2}
    )
    scheduler.start()
    logger.info("Scheduler started — affiliate sync every 15 minutes")
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Stats Tool",
    description="Mailing campaign stats platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes — registered FIRST so they take priority over the frontend catch-all
app.include_router(auth.router)
app.include_router(affiliates.router)
app.include_router(campaigns.router)
app.include_router(stats.router)
app.include_router(inbound.router)
app.include_router(outbound.router)
app.include_router(partner.router)
app.include_router(suggestions.router)
app.include_router(schedule.router)
app.include_router(sync.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# Frontend static files — registered LAST
FRONTEND_DIST = "/opt/stats-tool/frontend/dist"

if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_DIST}/assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(f"{FRONTEND_DIST}/index.html")
