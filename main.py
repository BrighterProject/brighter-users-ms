from pathlib import Path

import uvicorn as uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from ms_core import setup_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.logging import setup_logging
from app.settings import db_url

setup_logging()

application = FastAPI(title="brighter-users-ms", redirect_slashes=False)
application.state.limiter = limiter
application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.exception_handler(HTTPException)
async def http_exception_logging(request: Request, exc: HTTPException):
    logger.opt(exception=exc).error(f"HTTPException caught: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


tortoise_conf = setup_app(application, db_url, Path("app") / "routers", ["app.models"])
