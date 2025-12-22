from fastapi import APIRouter, Path, Query

from landuse_app.dependencies import renovation_potential
from landuse_app.exceptions.http_exception_wrapper import http_exception
from landuse_app.logic.constants.constants import VALID_SOURCES
from landuse_app.schemas import GeoJSON

urbanization_router = APIRouter(tags=["urbanization_level"])

@urbanization_router.get(
    "/scenarios/{scenario_id}/urbanization_level",
    response_model=GeoJSON,
    description=(
        "Function for getting urbanization level for a scenario. "
        "Additionally, returns layer in GeoJSON implemented in JSON response. "
        "Args: scenario_id (int): unique identifier of the scenario. "
        "Returns: GeoJSON: urbanization level data."
    ),
)
async def get_projects_urbanization_level(
    scenario_id: int = Path(..., description="The unique identifier of the scenario."),
    source: str = Query(
        None,
        description="The source of the landuse zones data. Available sources are: User, PZZ, OSM",
    ),
    year: int = Query(
        None,
        description="The year of the landuse zones data",
    ),
) -> GeoJSON:
    if source is not None and source not in VALID_SOURCES:
        raise http_exception(
            422,
            f"Invalid source. Valid sources are: {', '.join(VALID_SOURCES)}",
            source,
        )
    return await renovation_potential.get_urbanization_level(
        scenario_id, source=source, year=year
    )

@urbanization_router.get(
    "/scenarios/{scenario_id}/context/urbanization_level",
    response_model=GeoJSON,
    description=(
        "Function for getting urbanization level for a scenario's context. "
        "Additionally, returns layer in GeoJSON implemented in JSON response. "
        "Args: scenario_id (int): unique identifier of the scenario. "
        "Returns: GeoJSON: context urbanization level data."
    ),
)
async def get_projects_context_urbanization_level(
    scenario_id: int = Path(..., description="The unique identifier of the scenario."),
    source: str = Query(
        None,
        description="The source of the landuse zones data. Available sources are: User, PZZ, OSM",
    ),
    year: int = Query(
        None,
        description="The year of the landuse zones data",
    ),
) -> GeoJSON:
    if source is not None and source not in VALID_SOURCES:
        raise http_exception(
            422,
            f"Invalid source. Valid sources are: {', '.join(VALID_SOURCES)}",
            source,
        )
    return await renovation_potential.get_context_urbanization_level(
        scenario_id, source=source, year=year
    )