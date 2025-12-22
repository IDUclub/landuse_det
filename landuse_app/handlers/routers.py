"""Api routers are defined here."""

from fastapi import APIRouter

system_router = APIRouter(tags=["system"])
landuse_router = APIRouter(tags=["landuse"])



territories_urbanization_router = APIRouter(tags=["territories_urbanization"])


routers = [
    landuse_router,
    territories_urbanization_router,
    system_router,
]

__all__ = [
    "routers",
]
