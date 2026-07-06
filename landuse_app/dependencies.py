from pathlib import Path

from landuse_app.broker_handlers.base_scenario_created_handler import BaseScenarioCreatedHandler
from landuse_app.common.consumer_wrapper import ConsumerWrapper
from landuse_app.common.producer_wrapper import ProducerWrapper
from loguru import logger
from iduconfig import Config

from landuse_app.config import ConfigUtils
from landuse_app.logic.api.urban_db_api_client import RequestHandler
from landuse_app.logic.auth.auth_client import AuthenticationClient
from landuse_app.logic.auth.auth_config import build_auth_config
from landuse_app.logic.auth.service_token import ServiceTokenProvider
from landuse_app.logic.helpers.indicators_service import IndicatorsService
from landuse_app.logic.helpers.interpretation_service import InterpretationService
from landuse_app.logic.helpers.preprocessing_service import PreProcessingService
from landuse_app.logic.helpers.renovation_potential import RenovationPotential
from landuse_app.logic.helpers.spatial_methods import SpatialMethods
from landuse_app.logic.helpers.territories_urbanization import TerritoriesUrbanization
from landuse_app.logic.helpers.urban_api_access import UrbanAPIAccess
from landuse_app.observability.otel_agent import OpenTelemetryAgent
from storage.caching import CachingService


config = Config()
logger.add(
    f'{config.get("LOG_FILE")}.log',
    colorize=False,
    backtrace=True,
    diagnose=True
)


cache_enabled = bool(config.get("CACHE_ENABLED"))
caching_service = CachingService(Path().absolute() / "__landuse_cache__", cache_enabled)

utilscofig = ConfigUtils()

auth_config = build_auth_config()
auth_client = AuthenticationClient(auth_config)
service_token_provider = ServiceTokenProvider(auth_config)

requests_handler = RequestHandler(
    config.get("URBAN_API"), service_token_provider, caching_service
)

urban_api = UrbanAPIAccess(requests_handler, config)

spatial_methods = SpatialMethods()
indicators_service = IndicatorsService(urban_api, spatial_methods)
interpretation_service = InterpretationService()
preprocessing_service = PreProcessingService(urban_api)
renovation_potential = RenovationPotential(caching_service, interpretation_service, urban_api, preprocessing_service)
territory_urbanization = TerritoriesUrbanization(caching_service, urban_api, preprocessing_service, renovation_potential)

consumer = ConsumerWrapper()
producer = ProducerWrapper()

otel_agent: OpenTelemetryAgent | None = None

consumer.register_handler(
    BaseScenarioCreatedHandler(renovation_potential, producer.producer_service, urban_api, indicators_service)
)