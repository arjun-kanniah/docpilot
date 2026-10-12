from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from docpilot import __version__
from docpilot.api import router
from docpilot.config import Settings, get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DocPilot API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health(current: Annotated[Settings, Depends(get_settings)]) -> dict[str, str | bool]:
        return {
            "status": "ok",
            "version": __version__,
            "env": current.env,
            "demo": current.demo_mode,
        }

    app.include_router(router)
    if settings.static_dir is not None:
        # The built web app, served after the API routes so /api/* always reaches the API
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="web")
    return app


app = create_app()
