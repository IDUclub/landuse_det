from confluent_kafka import Message
from loguru import logger
from otteroad import BaseMessageHandler
from otteroad.consumer.handlers.base import EventT
from otteroad.models.scenario_events.projects.ScenarioZonesUpdated import (
    ScenarioZonesUpdated,
)

from landuse_app.broker_handlers.project_indicators import (
    ProjectIndicatorsRecalculator,
    run_step,
)


class ScenarioZonesUpdatedHandler(BaseMessageHandler[ScenarioZonesUpdated]):
    """Functional zones of a project scenario were saved: recalculate its land-use balance."""

    def __init__(self, recalculator: ProjectIndicatorsRecalculator):
        self.recalculator = recalculator
        super().__init__()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    async def handle(self, event: EventT, ctx: Message = None):
        logger.info(f"Received {type(event)}")
        logger.info(f"project: {event.project_id}, scenario: {event.scenario_id}")

        await run_step(
            "zone_balance",
            self.recalculator.recalculate_zone_balance(event.scenario_id),
            scenario_id=event.scenario_id,
            project_id=event.project_id,
            event_type=type(event).__name__,
        )
