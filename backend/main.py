import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from backend.auth.router import router as auth_router
from backend.config import settings
from backend.database import close_db, init_db
from backend.exceptions import (
    MediaForgeError,
    mediaforge_exception_handler,
    unhandled_exception_handler,
)
from backend.logging_config import get_logger, request_id_var, setup_logging
from backend.modules.discovery.router import router as discovery_router
from backend.modules.setup.router import router as setup_router
from backend.modules.downloads.router import router as downloads_router
from backend.modules.indexers.router import router as indexers_router
from backend.modules.livetv.router import router as livetv_router
from backend.modules.movies.router import router as movies_router
from backend.modules.series.router import router as series_router
from backend.modules.subtitles.router import router as subtitles_router
from backend.modules.iptv.router import router as iptv_router
from backend.modules.vpn.router import router as vpn_router
from backend.system.router import router as system_router
from backend.websocket_manager import manager

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("mediaforge_starting", version="2.0.0")

    # Initialize database
    await init_db()

    # Initialize Redis (optional, graceful if unavailable)
    try:
        from backend.redis import init_redis
        await init_redis()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))

    # Ensure directory structure
    try:
        from backend.services.file_manager import ensure_directories
        ensure_directories()
    except Exception:
        pass

    # Check frontend
    frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
    has_frontend = frontend_path.exists() and (frontend_path / "index.html").exists()
    logger.info("frontend_check", path=str(frontend_path), exists=frontend_path.exists(), has_index=has_frontend)

    logger.info("mediaforge_ready", port=settings.APP_PORT)

    yield

    # Shutdown
    logger.info("mediaforge_shutting_down")

    try:
        from backend.redis import close_redis
        await close_redis()
    except Exception:
        pass

    await close_db()
    logger.info("mediaforge_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="MediaForge",
        description="Unified media management — single pane of glass for your arr stack",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        redirect_slashes=False,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = str(uuid.uuid4())[:8]
        request_id_var.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # Exception handlers
    app.add_exception_handler(MediaForgeError, mediaforge_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # API Routers
    api_prefix = "/api/v1"
    app.include_router(setup_router, prefix=api_prefix)
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(discovery_router, prefix=api_prefix)
    app.include_router(movies_router, prefix=api_prefix)
    app.include_router(series_router, prefix=api_prefix)
    app.include_router(indexers_router, prefix=api_prefix)
    app.include_router(downloads_router, prefix=api_prefix)
    app.include_router(subtitles_router, prefix=api_prefix)
    app.include_router(iptv_router, prefix=api_prefix)
    app.include_router(livetv_router, prefix=api_prefix)
    app.include_router(vpn_router, prefix=api_prefix)
    app.include_router(system_router, prefix=api_prefix)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, token: str = ""):
        user_id = "anonymous"
        if token:
            try:
                from backend.auth.service import decode_jwt
                payload = decode_jwt(token)
                user_id = payload.get("sub", "anonymous")
            except Exception:
                pass

        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(websocket, user_id)

    # Serve frontend (SPA with client-side routing)
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static-assets")

        from fastapi.responses import FileResponse

        index_html = frontend_dist / "index.html"

        @app.get("/")
        async def root_page():
            return FileResponse(
                str(index_html),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

        @app.get("/mediaforge-logo.svg")
        async def logo():
            logo_path = frontend_dist / "mediaforge-logo.svg"
            if logo_path.exists():
                return FileResponse(str(logo_path))

        # SPA catch-all
        @app.get("/{path:path}")
        async def spa_catch_all(path: str):
            file_path = frontend_dist / path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(index_html))

    return app


app = create_app()
