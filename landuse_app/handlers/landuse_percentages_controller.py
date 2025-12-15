from fastapi import APIRouter, Path, Query

from landuse_app.dependencies import renovation_potential
from landuse_app.exceptions.http_exception_wrapper import http_exception
from landuse_app.logic.constants.constants import VALID_SOURCES

landuse_percentages_router = APIRouter(tags=["landuse_percentages"])

@landuse_percentages_router.get(
    "/scenarios/{scenario_id}/landuse_percentages",
    response_model=dict,
    description=(
        "Function for getting land use percentages for a scenario. "
        "Args: scenario_id (int): unique identifier of the scenario. "
        "Returns: dict: land use percentages data."
    ),
)
async def get_project_landuse_parts(
    scenario_id: int = Path(..., description="The unique identifier of the scenario."),
    source: str = Query(
        None,
        description="The source of the landuse zones data. Available sources are: User, PZZ, OSM",
    ),
    year: int = Query(
        None,
        description="The year of the landuse zones data",
    ),
) -> dict:
    if source is not None and source not in VALID_SOURCES:
        raise http_exception(
            422,
            f"Invalid source. Valid sources are: {', '.join(VALID_SOURCES)}",
            source,
        )
    return await renovation_potential.get_project_landuse_parts(
        scenario_id, source=source, year=year
    )