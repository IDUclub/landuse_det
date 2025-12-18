# from iduconfig import Config
# from otteroad.models.scenario_events.projects.ScenarioObjectsUpdated import ScenarioObjectsUpdated
#
# from landuse_app.logic.helpers.urban_api_access import UrbanAPIAccess
#
# ScenarioObjectsUpdated
#
# from confluent_kafka import Message
# from loguru import logger
# from otteroad import BaseMessageHandler, KafkaProducerClient
# from otteroad.consumer.handlers.base import EventT
# from otteroad.models.scenario_events.projects.BaseScenarioCreated import BaseScenarioCreated
#
#
# class ScenarioObjectsUpdatedHandler(BaseMessageHandler[ScenarioObjectsUpdated]):
#     def __init__(
#             self,
#             config: Config,
#             urban_api: UrbanAPIAccess,
#             producer: KafkaProducerClient
#     ):
#         super().__init__()
#
#     async def on_startup(self):
#         pass
#
#     async def on_shutdown(self):
#         pass
#     #FIXME
#     # async def handle(self, event: EventT, ctx: Message):
#     #     logger.info(f"{type(event)}")
#     #     logger.info(event.project_id)
#
#     async def handle(self, event: EventT, ctx: Message):
#         logger.info(f"Received {type(event)}")
#         logger.info(
#             f"base scenario: {event.base_scenario_id}, project: {event.project_id}, regional scenario: {event.regional_scenario_id}")
#         scenario_id = event.base_scenario_id
#         try:
#             project_scenario = await self.urban_api.get_scenario_by_id(scenario_id, self.config.get("URBAN_API_TOKEN"))
#         except HTTPException as e:
#             if e.status_code == 404:
#                 logger.info(f"No project scenario {scenario_id}, skipping...")
#                 return
#             logger.error(str(e))
#             return
#         parent_scenario_id = project_scenario.get("parent_scenario", {}).get("id", None)
#         if parent_scenario_id is None:
#             logger.info("no regional scenario, skipping...")
#             return
#
#         regional_scenario = await self.urban_api.get_scenario_by_id(parent_scenario_id,
#                                                                     self.config.get("URBAN_API_TOKEN"))
#         territory_id = regional_scenario.get("project", {}).get("region", {}).get("id", None)
#         if territory_id is None:
#             logger.info(f"Parent scenario is not regional or no response {regional_scenario}, skipping...")
#             return
#
#         try:
#             project_geometry = await self.urban_api.get_project_geometry(scenario_id,
#                                                                          self.config.get("URBAN_API_TOKEN"))
#         except HTTPException as e:
#             if e.status_code == 404:
#                 logger.info(f"No project geometry for scenario {scenario_id}, skipping...")
#                 return
#             logger.error(str(e))
#             return
#         grid = GeoDataFrame(geometry=[project_geometry], crs=4326)
#         logger.info(f"Prepared project geometry")
#
#         tasks = [
#             self.put_social_evaluation(grid, territory_id, scenario_id, event.project_id),
#             self.put_engineering_evaluation(grid, territory_id, scenario_id, event.project_id)
#         ]
#         await asyncio.gather(*tasks)