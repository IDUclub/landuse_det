from fastapi import APIRouter, Path, Query

from landuse_app.dependencies import indicators_service
from landuse_app.exceptions.http_exception_wrapper import http_exception
from landuse_app.logic.constants.constants import VALID_SOURCES

indicators_router = APIRouter(tags=["indicators"])

@indicators_router.post(
    "/indicators/{territory_id}/calculate_territory_urbanization",
    response_model=dict | list[dict],
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "indicator": {
                            "indicator_id": 16,
                            "parent_id": 3,
                            "name_full": "Степень урбанизации территории",
                            "measurement_unit": {"id": 3, "name": "%"},
                            "level": 2,
                            "list_label": "1.3",
                        },
                        "territory": {"id": 13, "name": "Сабское сельское поселение"},
                        "date_type": "year",
                        "date_value": "2025-01-01",
                        "value": 10.65,
                        "value_type": "forecast",
                        "information_source": "landuse_det",
                        "created_at": "2025-03-13T11:44:46.727723Z",
                        "updated_at": "2025-03-13T11:44:46.727723Z",
                    }
                }
            },
        },
        422: {"description": "Validation Error"},
    },
    description=(
            "Calculates and saves the urbanization percentage for a given territory in Urban DB. "
            "Returns a dictionary containing the computed indicator data that was saved in Urban DB."
    ),
)
async def get_territory_urbanization_level(
        territory_id: int = Path(
            ..., description="The unique identifier of the territory."
        ),
        source: str = Query(
            None,
            description="The source of the landuse zones data. Valid options: User, PZZ, OSM.",
        ),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
) -> dict | list[dict]:
    """
    Calculate and store the urbanization percentage for a given territory in Urban DB.

    **Parameters**:
    - **territory_id** (int): The unique identifier of the territory.
    - **source** (str, optional): The source of the landuse zones data. Valid options: PZZ or OSM. Defaults to None.
    - **force_recalculate** (bool, optional): If set to True, forces recalculation even if the indicator exists. Defaults to False.

    **Returns**:
    - **dict**: A dictionary containing the computed urbanization indicator data.

    **Raises**:
    - **HTTPException (422)**: If the provided `source` is invalid.
    """
    if source is not None and source not in VALID_SOURCES:
        raise http_exception(
            422,
            f"Invalid source. Valid sources are: {', '.join(VALID_SOURCES)}",
            source,
        )
    return await indicators_service.get_territory_urbanization_level(
        territory_id, source=source, force_recalculate=force_recalculate
    )


@indicators_router.post(
    "/indicators/{territory_id}/calculate_area_indicator",
    response_model=dict | list[dict],
    description="Calculate and store the area indicator for a given territory in Urban DB.",
)
async def calculate_area_indicator(
        territory_id: int = Path(
            ..., description="The unique identifier of the territory."
        ),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
) -> dict | list[dict]:
    territory_area = await indicators_service.calculate_territory_area(
        territory_id, force_recalculate=force_recalculate
    )
    return territory_area


@indicators_router.post(
    "/indicators/{territory_id}/services_count_indicator",
    description="Calculate the number of services indicators for a given territory.",
)
async def services_count_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        indicator_id: int = Query(description="The unique identifier of the indicator."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
) -> dict | list[dict]:
    services_count = await indicators_service.calculate_service_count(
        territory_id, indicator_id, force_recalculate=force_recalculate
    )
    return services_count


@indicators_router.post(
    "/indicators/{project_id}/calculate_project_area_indicator",
    description="Calculate and store the area indicator for a given project in Urban DB.",
)
async def calculate_project_area_indicator(
        project_id: int = Path(description="The unique identifier of the territory."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
):
    project_area = await indicators_service.calculate_project_territory_area(
        project_id, force_recalculate=force_recalculate
    )
    return project_area


@indicators_router.post(
    path="/indicators/{territory_id}/population_density_indicator",
    description="Calculate and store the population density indicator for a given territory in Urban DB.",
)
async def population_density_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
):
    population_density = await indicators_service.population_density(
        territory_id, force_recalculate
    )
    return population_density


@indicators_router.post(
    path="/indicators/{territory_id}/target_cities_indicator",
    description="Calculate and store the target cities indicator for a given territory in Urban DB.",
)
async def target_cities_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
):
    target_cities_count = await indicators_service.target_cities(
        territory_id, force_recalculate=force_recalculate
    )
    return target_cities_count


@indicators_router.post(
    path="/indicators/{territory_id}/cities_indicator/{indicator_id}",
    description="""
        Calculate and store the chosen city indicator for a given territory in Urban DB.
        Choose the city indicator for a given territory:

        Количество крупных (население от 100 000 человек) городов на территории (`indicator_id = 10`)
        Количество средних (население от 50 000 до 100 000 человек) городов на территории (`indicator_id = 11`)
        Количество малых (население менее 50 000 человек) городов на территории (`indicator_id = 12`)
        """,
)
async def cities_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        indicator_id: int = Path(
            description="The unique identifier of the indicator city size."
        ),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
):
    big_cities_count = await indicators_service.city_size_indicator(
        territory_id, indicator_id, force_recalculate=force_recalculate
    )
    return big_cities_count


@indicators_router.post(
    path="/indicators/{territory_id}/engineering_infrastructure_indicator",
    description="Calculate and store number of engineering objects indicator on given territory in Urban DB",
)
async def engineering_infrastructure_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
):
    engineering_infrastructure_count = (
        await indicators_service.engineering_infrastructure(
            territory_id, force_recalculate=force_recalculate
        )
    )
    return engineering_infrastructure_count


@indicators_router.post(
    path="/indicators/{territory_id}/recreation_area",
    description="Calculate and store recreation area indicator for a given territory in Urban DB.",
)
async def recreation_area_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
        source: str = Query(
            None,
            description="The source of the landuse zones data. Available sources are: User, PZZ, OSM",
        ),
):
    recreation_area = await indicators_service.recreation_area(
        territory_id, force_recalculate=force_recalculate, source=source
    )
    return recreation_area


@indicators_router.post(
    path="/indicators/{territory_id}/oopt",
    description="Calculate and store 'Особо охраняемые природные территории' indicator for a given territory in Urban DB.",
)
async def oop_indicator(
        territory_id: int = Path(description="The unique identifier of the territory."),
        force_recalculate: bool = Query(
            False,
            description="If True, forces recalculation even if the indicator already exists.",
        ),
):
    oopt_parts_count = await indicators_service.oopt_parts(
        territory_id, force_recalculate=force_recalculate
    )
    return oopt_parts_count