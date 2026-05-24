from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.middleware import limiter, register_exception_handlers
from app.core.config import settings

try:
	from app.api.router import router as api_router
except Exception:  # pragma: no cover - fallback while router is being implemented
	api_router = APIRouter()


logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s %(levelname)s %(name)s %(message)s",
	datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ai_trust_analyzer")


@asynccontextmanager
async def lifespan(_: FastAPI):
	logger.info("Application ready")
	yield
	logger.info("Application stopping gracefully")


def create_app() -> FastAPI:
	app = FastAPI(
		title="AI Trust Analyzer",
		version="0.1.0",
		description="Analyze AI responses for trustworthiness and hallucination risk.",
		lifespan=lifespan,
	)

	app.add_middleware(
		CORSMiddleware,
		allow_origins=settings.ALLOWED_ORIGINS,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	app.state.limiter = limiter
	register_exception_handlers(app)

	app.include_router(api_router)

	@app.get("/")
	async def root() -> dict[str, str]:
		return {"status": "ok"}

	return app


app = create_app()


if __name__ == "__main__":
	uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
