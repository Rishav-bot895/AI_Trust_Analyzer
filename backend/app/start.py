from __future__ import annotations

import os

import uvicorn


def _log(message: str) -> None:
    print(message, flush=True)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    _log(f"Starting AI Trust Analyzer on port {port}")
    _log("Importing FastAPI application")

    from app.main import app

    _log("FastAPI application imported")
    _log("Starting Uvicorn server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
