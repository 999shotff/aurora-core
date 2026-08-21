"""AURORA CORE Production Server Entry Point.

Usage:
    python -m aurora.market.server

Or with uvicorn directly:
    uvicorn aurora.market.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn


def main() -> None:
    """Start the production server."""
    host = os.environ.get("AURORA_HOST", "0.0.0.0")
    port = int(os.environ.get("AURORA_PORT", "8000"))
    log_level = os.environ.get("AURORA_LOG_LEVEL", "info")
    debug = os.environ.get("AURORA_DEBUG", "false").lower() == "true"

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    logger = logging.getLogger("aurora.server")
    logger.info("Starting AURORA CORE v0.2.0")
    logger.info("Data mode: %s", os.environ.get("AURORA_DATA_MODE", "demo"))
    logger.info("CORS origins: %s", os.environ.get("AURORA_CORS_ORIGINS", "https://aurora-core.vercel.app"))
    logger.info("Listening on %s:%d", host, port)

    uvicorn.run(
        "aurora.market.api:app",
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
