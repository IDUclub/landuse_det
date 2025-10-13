import asyncio

import pandas as pd
from loguru import logger

from landuse_app import config
from landuse_app.exceptions.http_exception_wrapper import http_exception
from landuse_app.logic.api import urban_db_api


async def get_projects_territory(project_id: int) -> dict:
    """
    Fetches the territory information for a project.

    Parameters:
    project_id (int): ID of the project.

    Returns:
    dict: Territory information.
    """
    endpoint = f"/api/v1/projects/{project_id}/territory"
    headers = {
        "Authorization": f"Bearer {config.get('ACCESS_TOKEN')}"""
    }
    response = await urban_db_api.get(endpoint)

    if not response:
        raise http_exception(404, f"No territory information found for project ID:", project_id)

    return response


async def get_projects_base_scenario_id(project_id: int) -> int:
    """
    Fetches the base scenario ID for a project.

    Parameters:
    project_id (int): ID of the project.

    Returns:
    int: Base scenario ID.
    """
    endpoint = f"/api/v1/projects/{project_id}/scenarios"
    scenarios = await urban_db_api.get(endpoint)

    for scenario in scenarios:
        if scenario.get("is_based"):
            return scenario.get("scenario_id")


async def get_functional_zone_sources(
    scenario_id: int,
    source: str | None = None,
    year: int | None = None
) -> dict:
    """
    Fetch available functional zone sources for a given scenario ID and determine the best source.

    Parameters:
    scenario_id (int): The ID of the scenario.
    source (str, optional): The preferred source (PZZ or OSM). If not provided, the best source is selected automatically.

    Returns:
    dict: The most relevant functional zone source data.

    Raises:
    http_exception: If no sources are found or the specified source is not available.
    """
    endpoint = f"/api/v1/scenarios/{scenario_id}/functional_zone_sources"
    response = await urban_db_api.get(endpoint)

    if not response:
        raise http_exception(404, f"Data not found for scenario", scenario_id)

    filtered_sources = _filter_sources(response, source, year)

    if filtered_sources:
        return await _form_source_params(filtered_sources)

    if source or year:
        raise http_exception(404, f"Data not found for scenario {scenario_id}", {"source": source, "year": year})

    return await _form_source_params(response)


def _filter_sources(sources: list[dict], source: str | None, year: int | None) -> list[dict]:
    filtered = sources

    if source:
        filtered = [s for s in filtered if s.get("source") == source]

    if year:
        filtered = [s for s in filtered if s.get("year") == year]

    return filtered


async def _form_source_params(sources: list[dict]) -> dict:
    if not sources:
        raise http_exception(404, "No sources are available to choose from")

    if len(sources) == 1:
        return sources[0]

    source_data_df = pd.DataFrame(sources)
    source_priority = ["Unknown Source", "User", "PZZ", "OSM"]

    for preferred_source in source_priority:
        if preferred_source in source_data_df["source"].unique():
            return (
                source_data_df[source_data_df["source"] == preferred_source]
                .sort_values("year", ascending=False)
                .iloc[0]
                .to_dict()
            )

    return source_data_df.sort_values("year", ascending=False).iloc[0].to_dict()


async def get_functional_zones_scenario_id(scenario_id: int, is_context: bool = False, source: str = None) -> dict:
    """
    Fetches functional zones for a project with an optional context flag and source selection.

    Parameters:
    project_id (int): ID of the project.
    is_context (bool): Flag to determine if context data should be fetched. Default is False.
    source (str, optional): The preferred source (PZZ or OSM). If not provided, the best source is selected automatically.

    Returns:
    dict: Response data from the API.

    Raises:
    http_exception: If the response is empty or the specified source is not available.
    """
    # base_scenario_id = await get_projects_base_scenario_id(scenario_id)
    source_data = await get_functional_zone_sources(scenario_id, source)

    if not source_data or "source" not in source_data or "year" not in source_data:
        raise http_exception(404, "No valid source found for the given project ID", scenario_id)

    source = source_data["source"]
    year = source_data["year"]

    if is_context:
        endpoint = f"/api/v1/scenarios/{scenario_id}/context/functional_zones?year={year}&source={source}"
    else:
        endpoint = f"/api/v1/scenarios/{scenario_id}/functional_zones?year={year}&source={source}"

    response = await urban_db_api.get(endpoint)
    if not response or "features" not in response or not response["features"]:
        raise http_exception(404, "No functional zones found for the given project ID", scenario_id)

    return response


async def get_all_physical_objects_geometries(scenario_id: int, is_context: bool = False) -> dict:
    """
    Fetches all physical object geometries for a project, optionally for context.

    Parameters:
        scenario_id (int): ID of the project.
        is_context (bool): Whether to fetch context geometries.

    Returns:
        dict: The API response containing geometries.

    Raises:
        http_exception: If the response is empty.
    """
    # base_scenario_id = await get_projects_base_scenario_id(scenario_id)

    endpoint = (
        f"/api/v1/scenarios/{scenario_id}/context/geometries_with_all_objects"
        if is_context
        else f"/api/v1/scenarios/{scenario_id}/geometries_with_all_objects"
    )

    try:
        response = await urban_db_api.get(endpoint)
    except Exception as e:
        raise http_exception(404, "No geometries found for the given scenario ID:", str(e))

    return response


async def get_all_physical_objects_geometries_type_id(scenario_id: int, object_type_id: int) -> dict:
    return await urban_db_api.get(
        f"/api/v1/scenarios/{scenario_id}/geometries_with_all_objects?physical_object_type_id={object_type_id}"
    )


async def get_functional_zones_scen_id_percentages(scenario_id: int, source: str = None) -> dict:
    """
    Fetches functional zone percentages for a given scenario ID with an optional source selection.

    Parameters:
    scenario_id (int): The ID of the scenario.
    source (str, optional): The preferred source (PZZ or OSM). If not provided, the best source is selected automatically.

    Returns:
    dict: Response data from the API.

    Raises:
    http_exception: If the response is empty or the specified source is not available.
    """
    source_data = await get_functional_zone_sources(scenario_id, source)

    if not source_data or "source" not in source_data or "year" not in source_data:
        raise http_exception(404, "No valid source found for the given scenario ID", scenario_id)

    source = source_data["source"]
    year = source_data["year"]

    endpoint = f"/api/v1/scenarios/{scenario_id}/functional_zones?year={year}&source={source}"
    response = await urban_db_api.get(endpoint)

    if not response or "features" not in response or not response["features"]:
        raise http_exception(404, "No functional zones found for the given scenario ID", scenario_id)

    return response


async def get_all_physical_objects_geometries_scen_id_percentages(scenario_id: int) -> dict:
    """
    Fetches all physical object geometries for a project, optionally for context.

    Parameters:
        scenario_id (int): ID of the scenario.
    Returns:
        dict: The API response containing geometries.

    Raises:
        http_exception: If the response is empty.
    """
    endpoint = f"/api/v1/scenarios/{scenario_id}/geometries_with_all_objects"
    response = await urban_db_api.get(endpoint)

    if not response or "features" not in response or not response["features"]:
        raise http_exception(404, "No functional zones found for the given scenario ID:", scenario_id)

    return response


async def get_functional_zone_sources_territory_id(territory_id: int, source: str = None) -> dict:
    """
        Fetch available functional zone sources for a given scenario ID and determine the best source.

        Parameters:
        scenario_id (int): The ID of the scenario.
        source (str, optional): The preferred source (PZZ or OSM). If not provided, the best source is selected automatically.

        Returns:
        dict: The most relevant functional zone source data.

        Raises:
        http_exception: If no sources are found or the specified source is not available.
        """
    endpoint = f"/api/v1/territory/{territory_id}/functional_zone_sources"
    response = await urban_db_api.get(endpoint)

    if not response:
        raise http_exception(404, f"No functional zone sources found for the given territory id ID", territory_id)

    if source:
        source_data = next((s for s in response if s["source"] == source), None)
        if not source_data:
            raise http_exception(404, f"No data found for the specified source", source)
        return source_data

    return await _form_source_params(response)


async def get_functional_zones_territory_id(territory_id: int, source: str = None, functional_zone_type_id: int = None,
                                            params: dict = None) -> dict:
    """
        Fetches functional zones for a project with an optional context flag and source selection.

        Parameters:
        project_id (int): ID of the project.
        is_context (bool): Flag to determine if context data should be fetched. Default is False.
        source (str, optional): The preferred source (PZZ or OSM). If not provided, the best source is selected automatically.

        Returns:
        dict: Response data from the API.

        Raises:
        http_exception: If the response is empty or the specified source is not available.
        """
    source_data = await get_functional_zone_sources_territory_id(territory_id, source)

    if not source_data or "source" not in source_data or "year" not in source_data:
        raise http_exception(404, "No valid source found for the given project ID", territory_id)

    source = source_data["source"]
    year = source_data["year"]

    if functional_zone_type_id:
        endpoint = (
            f"/api/v1/territory/{territory_id}/functional_zones?year={year}&source={source}&functional_zone_type_id={functional_zone_type_id}"
        )
    else:
        endpoint = (
            f"/api/v1/territory/{territory_id}/functional_zones?year={year}&source={source}"
        )

    response = await urban_db_api.get(endpoint, params=params)
    if not response:
        raise http_exception(404, "No functional zones found for the given project ID", territory_id)

    return response


async def get_functional_zones_geojson_territory_id(territory_id: int, source: str = None,
                                                    functional_zone_type_id: int = None, params: dict = None) -> dict:
    source_data = await get_functional_zone_sources_territory_id(territory_id, source)
    if not source_data or "source" not in source_data or "year" not in source_data:
        raise http_exception(404, "No valid source found for the given project ID", territory_id)
    source = source_data["source"]
    year = source_data["year"]
    if functional_zone_type_id:
        endpoint = (
            f"/api/v1/territory/{territory_id}/functional_zones?year={year}&source={source}&functional_zone_type_id={functional_zone_type_id}"
        )
    else:
        endpoint = (f"/api/v1/territory/{territory_id}/functional_zones?year={year}&source={source}"
                    )

    response = await urban_db_api.get(endpoint, params=params)
    return response


async def get_target_cities(territory_id: int) -> dict:
    endpoint = f"/api/v1/all_territories_without_geometry?parent_id={territory_id}&page_size=5000&get_all_levels=true&cities_only=true"
    response = await urban_db_api.get(endpoint)
    return response


async def get_physical_objects_from_territory(territory_id: int) -> dict:
    """
    Fetches all physical object geometries for a territory.

    Parameters:
        territory_id (int): ID of the territory.

    Returns:
        dict: The API response containing geometries.

    Raises:
        http_exception: If the response is empty.
    """

    endpoint = (
        f"/api/v1/territory/{territory_id}/physical_objects_geojson"
    )

    response = await urban_db_api.get(endpoint)
    if not response or "features" not in response or not response["features"]:
        raise http_exception(404, "No physical objects found for the given territory ID:", territory_id)

    return response


async def get_physical_objects_without_geometry(territory_id: int, params: dict = None) -> dict:
    endpoint = (
        f"/api/v1/territory/{territory_id}/physical_objects"
    )
    response = await urban_db_api.get(endpoint, params=params)
    return response


async def check_urbanization_indicator_exists(territory_id: int) -> dict | None:
    """
    Attempts to retrieve an existing urbanization indicator from the database.

    Returns:
      - dict: The indicator JSON if the response status is 200.
      - None: If the response status is 404 (i.e., the indicator does not exist).
    """
    endpoint = (
        f"/api/v1/territory/{territory_id}/indicator_values"
        "?indicator_id=16"
        f"&territory_id={territory_id}"
        "&date_type=year"
        "&date_value=2025-01-01"
        "&value_type=forecast"
        "&information_source=landuse_det"
    )
    data = await urban_db_api.get(endpoint, ignore_404=True)
    if not data:
        return None
    return data


async def check_indicator_exists(territory_id: int, indicator_id: int) -> dict | None:
    """
    Attempts to retrieve an existing indicator from the database.

    Returns:
      - dict: The indicator JSON if the response status is 200.
      - None: If the response status is 404 (i.e., the indicator does not exist).
    """
    endpoint = (
        f"/api/v1/territory/{territory_id}/indicator_values"
        f"?indicator_ids={indicator_id}"
        "&date_type=year"
        "&date_value=2025-01-01"
        "&value_type=real"
        "&information_source=modeled"
    )
    data = await urban_db_api.get(endpoint, ignore_404=True)
    if not data:
        return None
    return data


async def get_indicator_values(territory_id: int, indicator_id: int, params: dict = None) -> dict | None:
    endpoint = (
        f"/api/v1/territory/{territory_id}/indicator_values"
        f"?indicator_ids={indicator_id}"
    )
    response = await urban_db_api.get(endpoint, params=params)
    if not response:
        return None
    return response


async def put_indicator_value(indicator_data: dict) -> dict:
    """
    Creates or updates an indicator record in the database via a PUT request.

    Parameters:
      indicator_data (dict): A dictionary containing the indicator data, for example:
        {
            "indicator_id": 16,
            "territory_id": 113,
            "date_type": "year",
            "date_value": "2025-01-01",
            "value": 24.72,
            "value_type": "forecast",
            "information_source": "landuse_det"
        }

    Returns:
      dict: The JSON response from the API (the created or updated record).

    Raises:
      http_exception: If the response status code is not 200 or 201.
    """
    endpoint = "/api/v1/indicator_value"
    return await urban_db_api.put(endpoint, data=indicator_data)


async def get_physical_objects_from_territory_parallel(territory_id: int,
                                                       page_size: int = int(config.get("PAGE_SIZE"))) -> list[dict]:
    """
    Fetch physical objects from a territory in parallel with a concurrency limit of 5.

    This asynchronous function retrieves all physical objects for a given territory using the
    endpoint /territory/{territory_id}/physical_objects_with_geometry. It paginates through the results
    based on the provided page_size and uses the get() method from urban_db_api
    to make API requests. The function limits concurrent requests to 5.

    Parameters:
        territory_id (int): The unique identifier of the territory.
        page_size (int, optional): The number of objects to request per page (default is 5000).

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a physical object.
    """
    endpoint = f"/api/v1/territory/{territory_id}/physical_objects_with_geometry?page=1&page_size={page_size}"
    initial_response = await urban_db_api.get(endpoint)
    total = initial_response.get("count", 0)
    total_pages = (total // page_size) + (1 if total % page_size else 0)
    logger.info(f"Total physical objects on territory: {total}, Total number of pages: {total_pages}")

    urls = [
        f"/api/v1/territory/{territory_id}/physical_objects_with_geometry?page={i}&page_size={page_size}"
        for i in range(1, total_pages + 1)
    ]

    semaphore = asyncio.Semaphore(5)

    async def fetch_page_with_sem(url: str) -> dict:
        async with semaphore:
            data = await urban_db_api.get(url)
            logger.info(f"Page {url} has been loaded")
            return data

    tasks = [fetch_page_with_sem(url) for url in urls]
    pages = await asyncio.gather(*tasks)

    results = []
    for page in pages:
        results.extend(page.get("results", []))
    return results


async def get_territory_boundaries(territory_id: int) -> dict:
    endpoint = f"/api/v1/territory/{territory_id}"
    response = await urban_db_api.get(endpoint)
    if not response:
        raise http_exception(404, "No boundaries found for given territory ID:", territory_id)
    return response


async def get_service_type_id_through_indicator(indicator_id: int) -> int:
    endpoint = f"/api/v1/indicators/{indicator_id}"
    response = await urban_db_api.get(endpoint)
    service_type_id = response.get("service_type", 0)
    if isinstance(service_type_id, dict):
        service_type_id = service_type_id.get("id", 0)
    if not service_type_id:
        raise http_exception(404, "No assigned service found for given indicator ID:", indicator_id)
    return service_type_id


async def get_service_count(territory_id: int, service_type_id: int) -> int:
    endpoint = f"/api/v1/territory/{territory_id}/services"
    params = {
        "service_type_id": service_type_id,
        "page_size": 10
    }
    response = await urban_db_api.get(endpoint, params=params)
    if not response:
        raise http_exception(404, "No services found for given territory ID:", territory_id)
    number_of_services = response.get("count", 0)
    return number_of_services


async def get_services_geojson(territory_id: int, service_type_id: int, params: dict = None) -> dict:
    endpoint = f"/api/v1/territory/{territory_id}/services_geojson?service_type_id={service_type_id}"
    response = await urban_db_api.get(endpoint, params=params)
    if not response:
        raise http_exception(404, "No services found for given territory ID:", territory_id)
    return response


async def check_project_indicator_exist(project_id: int, indicator_id: int) -> dict | None:
    """
    Attempts to retrieve an existing indicator from the database.

    Returns:
      - dict: The indicator JSON if the response status is 200.
      - None: If the response status is 404 (i.e., the indicator does not exist).
    """
    scenario_id = await get_projects_base_scenario_id(project_id)
    endpoint = (
        f"/api/v1/scenarios/{scenario_id}/indicators_values"
        f"?indicator_ids={indicator_id}"
    )
    data = await urban_db_api.get(endpoint, ignore_404=True)
    if not data:
        return None
    return data


async def put_project_indicator(
        scenario_id: int,
        indicator_data: dict,
        *,
        use_token: bool = True,
        override_token: str | None = None,
        extra_headers: dict[str, str] | None = None
) -> dict:
    endpoint = f"/api/v1/scenarios/{scenario_id}/indicators_values"
    return await urban_db_api.put(
        endpoint,
        data=indicator_data,
        use_token=use_token,
        override_token=override_token,
        extra_headers=extra_headers
    )
