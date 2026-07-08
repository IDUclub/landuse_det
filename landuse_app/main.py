from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.responses import RedirectResponse

from landuse_app.auth_context import (
    extract_bearer_token,
    reset_current_bearer_token,
    set_current_bearer_token,
)
from landuse_app.dependencies import auth_service, config, consumer, producer
from landuse_app.handlers.indicators_controller import indicators_router
from landuse_app.handlers.landuse_percentages_controller import (
    landuse_percentages_router,
)
from landuse_app.handlers.renovation_controller import renovation_router
from landuse_app.handlers.urbanization_controller import urbanization_router

logger.add(
    f'{config.get("LOG_FILE")}.log', colorize=False, backtrace=True, diagnose=True
)
controllers = [
    indicators_router,
    landuse_percentages_router,
    urbanization_router,
    renovation_router,
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await consumer.start(["scenario.events"])
    await producer.start()
    try:
        yield
    finally:
        await consumer.stop()
        await producer.stop()
        await auth_service.aclose()


app = FastAPI(
    title="Landuse Det API",
    description="API for neudoby index",
    lifespan=lifespan,
    version="0.1.1",
    redirect_slashes=False,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def bind_request_bearer_token(request: Request, call_next):
    token_marker = set_current_bearer_token(
        extract_bearer_token(request.headers.get("Authorization"))
    )
    try:
        return await call_next(request)
    finally:
        reset_current_bearer_token(token_marker)


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse("/docs")


# application.include_router(admin_router)

# for controller in controllers:
#     application.include_router(controller.router)
for controller in controllers:
    app.include_router(controller)
