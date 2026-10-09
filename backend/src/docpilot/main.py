from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from docpilot import __version__
from docpilot.api import router
from docpilot.config import get_settings


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
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "env": settings.env}

    app.include_router(router)
    return app


app = create_app()
