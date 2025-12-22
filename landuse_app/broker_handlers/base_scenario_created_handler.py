from typing import Protocol

from landuse_app.logic.constants.constants import LAND_CATEGORY_NAME_TO_ID

from confluent_kafka import Message
from loguru import logger
from otteroad import BaseMessageHandler
from otteroad.consumer.handlers.base import EventT
from otteroad.models.scenario_events.projects.BaseScenarioCreated import BaseScenarioCreated

from landuse_app.logic.helpers.indicators_service import IndicatorsService
from landuse_app.logic.helpers.urban_api_access import UrbanAPIAccess


class RenovationCalculator(Protocol):
    async def calculate_zone_percentages(self, scenario_id: int) -> dict:
        ...


class Producer(Protocol):
    async def send(self, event) -> None:
        ...

class BaseScenarioCreatedHandler(BaseMessageHandler[BaseScenarioCreated]):
    def __init__(
            self,
            renovation: RenovationCalculator,
            producer: Producer,
            urban_api: UrbanAPIAccess,
            indicators: IndicatorsService

    ):
        self.renovation = renovation
        self.producer = producer
        self.urban_api = urban_api
        self.indicators = indicators
        super().__init__()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    async def handle(self, event: EventT, ctx: Message = None):
        logger.info(f"Received {type(event)}")
        logger.info(
            f"base scenario: {event.base_scenario_id}, project: {event.project_id}, regional scenario: {event.regional_scenario_id}")
        result = await self.renovation.calculate_zone_percentages(
            event.base_scenario_id
        )
        for zone_name, value in result.items():
            indicator_id = LAND_CATEGORY_NAME_TO_ID.get(zone_name)
            if indicator_id is None:
                logger.warning(
                    f"Unknown land category name '{zone_name}', skipping indicator calculation"
                )
                continue

            payload = {
                "indicator_id": indicator_id,
                "scenario_id": int(event.base_scenario_id),
                "territory_id": None,
                "hexagon_id": None,
                "value": float(value),
                "comment": "--",
                "information_source": "landuse_det",
                "properties": {},
            }
            await self.urban_api.put_project_indicator(
                event.base_scenario_id,
                payload
            )
            logger.info(
                f"Sending indicator {indicator_id} with name {zone_name} and value {value}"
                f"for scenario id {event.base_scenario_id}"
            )

        logger.info(f"Started project area calculation for {event.base_scenario_id}")
        await self.indicators.calculate_project_territory_area(project_id=event.project_id, force_recalculate=True)

        logger.info(f"AREA and ZONE BALANCE indicators for base scenario id {event.base_scenario_id} successful")
        return result
