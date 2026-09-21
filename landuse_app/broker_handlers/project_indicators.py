from typing import Protocol

from loguru import logger

from landuse_app.auth_context import service_scope
from landuse_app.logic.constants.constants import LAND_CATEGORY_NAME_TO_ID
from landuse_app.logic.helpers.indicators_service import IndicatorsService
from landuse_app.logic.helpers.urban_api_access import UrbanAPIAccess


class RenovationCalculator(Protocol):
    async def calculate_zone_percentages(self, scenario_id: int) -> dict:
        ...


class ProjectIndicatorsRecalculator:
    """
    Recalculates project indicators (territory area, land-use balance) and saves
    them to Urban DB. Used by Kafka handlers, so every call runs in the service
    scope: Keycloak service token + no file cache.
    """

    def __init__(
        self,
        renovation: RenovationCalculator,
        urban_api: UrbanAPIAccess,
        indicators: IndicatorsService,
    ):
        self.renovation = renovation
        self.urban_api = urban_api
        self.indicators = indicators

    async def recalculate_area(self, project_id: int) -> None:
        with service_scope():
            logger.info(f"Started project area calculation for project {project_id}")
            await self.indicators.calculate_project_territory_area(
                project_id=project_id,
                force_recalculate=True,
            )
            logger.info(f"AREA indicator for project {project_id} saved")

    async def recalculate_zone_balance(self, scenario_id: int) -> None:
        with service_scope():
            logger.info(f"Started zone balance calculation for scenario {scenario_id}")
            result = await self.renovation.calculate_zone_percentages(scenario_id)

            for zone_name, value in result.items():
                indicator_id = LAND_CATEGORY_NAME_TO_ID.get(zone_name)
                if indicator_id is None:
                    logger.warning(
                        f"Unknown land category name '{zone_name}', skipping indicator calculation"
                    )
                    continue

                payload = {
                    "indicator_id": indicator_id,
                    "scenario_id": int(scenario_id),
                    "territory_id": None,
                    "hexagon_id": None,
                    "value": float(value),
                    "comment": "--",
                    "information_source": "landuse_det",
                    "properties": {},
                }

                await self.urban_api.put_project_indicator(scenario_id, payload)

                logger.info(
                    f"Sending indicator {indicator_id} "
                    f"with name {zone_name} and value {value} "
                    f"for scenario id {scenario_id}"
                )
            logger.info(f"ZONE BALANCE indicators for scenario {scenario_id} saved")


async def run_step(step_name: str, coro, **log_extra) -> bool:
    """Runs one recalculation step; logs and swallows errors so the consumer keeps going."""
    try:
        await coro
        return True
    except Exception:
        logger.exception(
            f"Kafka message processing failed on step '{step_name}', skipping",
            extra=log_extra,
        )
        return False
