from confluent_kafka import Message
from loguru import logger
from otteroad import BaseMessageHandler
from otteroad.consumer.handlers.base import EventT
from otteroad.models.scenario_events.projects.BaseScenarioCreated import BaseScenarioCreated


class BaseScenarioCreatedHandler(BaseMessageHandler[BaseScenarioCreated]):
    def __init__(self):
        super().__init__()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass
    #FIXME
    async def handle(self, event: EventT, ctx: Message):
        logger.info(f"{type(event)}")
        logger.info(event.project_id)
