from pathlib import Path

from iduconfig import Config
from loguru import logger

from landuse_app.observability.config import PrometheusConfig
from landuse_app.observability.otel_agent import OpenTelemetryAgent
import landuse_app.dependencies as deps



async def start_prometheus():
    """
    Start the prometheus server
    """

    logger.info(f"Starting Prometheus server on {deps.config.get('PROMETHEUS_PORT')}")
    deps.otel_agent = OpenTelemetryAgent(
        prometheus_config=PrometheusConfig(
            host="0.0.0.0",
            port=int(deps.config.get("PROMETHEUS_PORT")),
        ),
    )
    logger.info(f"Prometheus server started on {deps.config.get('PROMETHEUS_PORT')}")


async def shutdown_prometheus():
    """
    Shutdowns prometheus service
    """

    logger.info("Shutting down Prometheus server")
    deps.otel_agent.shutdown()
    logger.info("Prometheus server was shut down")