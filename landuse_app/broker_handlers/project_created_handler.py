from confluent_kafka import Message
from loguru import logger
from otteroad import BaseMessageHandler
from otteroad.consumer.handlers.base import EventT
from otteroad.models.scenario_events.projects.ProjectCreated import ProjectCreated

from landuse_app.broker_handlers.project_indicators import (
    ProjectIndicatorsRecalculator,
    run_step,
)


class ProjectCreatedHandler(BaseMessageHandler[ProjectCreated]):
    """New project saved: compute territory area and land-use balance for its base scenario."""

    def __init__(self, recalculator: ProjectIndicatorsRecalculator):
        self.recalculator = recalculator
        super().__init__()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    async def handle(self, event: EventT, ctx: Message = None):
        logger.info(f"Received {type(event)}")
        logger.info(
            f"project: {event.project_id}, "
            f"base scenario: {event.base_scenario_id}, "
            f"territory: {event.territory_id}"
        )
        log_extra = {
            "scenario_id": event.base_scenario_id,
            "project_id": event.project_id,
            "event_type": type(event).__name__,
        }

        # Steps are independent: a failed area calculation must not block the zone balance.
        await run_step(
            "area", self.recalculator.recalculate_area(event.project_id), **log_extra
        )
        await run_step(
            "zone_balance",
            self.recalculator.recalculate_zone_balance(event.base_scenario_id),
            **log_extra,
        )
