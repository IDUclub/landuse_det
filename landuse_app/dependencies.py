from landuse_app.broker_handlers.base_scenario_created_handler import BaseScenarioCreatedHandler
from landuse_app.common.consumer_wrapper import ConsumerWrapper
from landuse_app.common.producer_wrapper import ProducerWrapper

consumer = ConsumerWrapper()
producer = ProducerWrapper()

consumer.register_handler(
    BaseScenarioCreatedHandler()
)
