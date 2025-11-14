from pathlib import Path

from landuse_app.broker_handlers.base_scenario_created_handler import BaseScenarioCreatedHandler
from landuse_app.common.consumer_wrapper import ConsumerWrapper
from landuse_app.common.producer_wrapper import ProducerWrapper

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from loguru import logger

from landuse_app import config
# from landuse_app.dependencies import consumer
from landuse_app.handlers import list_of_routes
from landuse_app.logic.api.urban_db_api_client import RequestHandler, AuthService
from landuse_app.logic.helpers import IndicatorsService
from landuse_app.logic.helpers.interpretation_service import InterpretationService
from landuse_app.logic.helpers.preprocessing_service import PreProcessingService
from landuse_app.logic.helpers.renovation_potential import RenovationPotential
from landuse_app.logic.helpers.spatial_methods import SpatialMethods
from landuse_app.logic.helpers.territories_urbanization import TerritoriesUrbanization
from landuse_app.logic.helpers.urban_api_access import UrbanAPIAccess
from storage.caching import CachingService

logger.add(
    f'{config.get("LOG_FILE")}.log', colorize=False, backtrace=True, diagnose=True
)


def bind_routes(application: FastAPI, prefix: str) -> None:
    """Bind all routes to application."""
    for route in list_of_routes:
        application.include_router(
            route, prefix=(prefix if "/" not in {r.path for r in route.routes} else "")
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await consumer.start(["scenario.events"])
    yield


def get_app(prefix: str = "/api") -> FastAPI:
    """Create application and all dependable objects."""

    application = FastAPI(
        title="Landuse Det API",
        description=config.get("API_DESCRIPTION"),
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
        openapi_url=f"{prefix}/openapi",
        version=f"{config.get('VERSION')} ({config.get('LAST_UPDATE')})",
        terms_of_service="http://swagger.io/terms/",
        license_info={
            "name": "Apache 2.0",
            "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
        },
    )
    bind_routes(application, prefix)

    @application.get(f"{prefix}/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=application.openapi_url,
            title=application.title + " - Swagger UI",
            oauth2_redirect_url=application.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://unpkg.com/swagger-ui-dist@5.11.7/swagger-ui-bundle.js",
            swagger_css_url="https://unpkg.com/swagger-ui-dist@5.11.7/swagger-ui.css",
        )

    origins = ["*"]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return application


app = get_app()

cache_enabled = config.get_bool("CACHE_ENABLED")  # должен вернуть True или False
caching_service = CachingService(Path().absolute() / "__landuse_cache__", cache_enabled)



requests_handler = RequestHandler(config.get("URBAN_API"), config.get("AUTH_SERVICE_URL"), caching_service)
auth_service = AuthService(config.get("AUTH_SERVICE_URL"))
urban_api = UrbanAPIAccess(requests_handler)

spatial_methods = SpatialMethods()
indicators_service = IndicatorsService(urban_api, spatial_methods)
interpretation_service = InterpretationService()
preprocessing_service = PreProcessingService(urban_api)
renovation_potential = RenovationPotential(caching_service, interpretation_service, urban_api, preprocessing_service)
territory_urbanization = TerritoriesUrbanization(caching_service, urban_api, preprocessing_service, renovation_potential)



consumer = ConsumerWrapper()
producer = ProducerWrapper()

consumer.register_handler(
    BaseScenarioCreatedHandler()
)
