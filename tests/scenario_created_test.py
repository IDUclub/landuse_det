import pytest

from landuse_app.broker_handlers.base_scenario_created_handler import (
    BaseScenarioCreatedHandler,
)
from otteroad.models.scenario_events.projects.BaseScenarioCreated import (
    BaseScenarioCreated,
)


class DummyProducer:
    async def send(self, event) -> None:
        pass


class FakeRenovationPotential:
    def __init__(self):
        self.called_with: list[int] = []

    async def calculate_zone_percentages(self, scenario_id: int) -> dict:
        self.called_with.append(scenario_id)
        return {
            "Земли общественно-делового назначения": 3.75,
            "Земли промышленного назначения": 9.52,
            "Земли рекреационного назначения": 13.9,
            "Земли жилой застройки": 17.01,
            "Земли специального назначения": 21.14,
            "Земли транспортного назначения": 10.79,
            "Земли водного фонда": 1.07,
            "Земли зелёных насаждений": 0.02,
            "Земли лесных массивов": 3.85,
            "Земли сельскохозяйственного назначения": 0,
            "Иные категории земель": 18.96,
        }


class FakeUrbanAPI:
    def __init__(self):
        self.saved_indicators: list[dict] = []
        self.requested_projects: list[int] = []

    async def get_projects_territory(self, project_id: int) -> dict:
        self.requested_projects.append(project_id)
        return {"project_territory_id": 77}

    async def put_project_indicator(self, scenario_id: int, payload: dict) -> None:
        self.saved_indicators.append(
            {
                "scenario_id": scenario_id,
                "payload": payload,
            }
        )


@pytest.mark.asyncio
async def test_base_scenario_created_handler_payloads():
    fake_renovation = FakeRenovationPotential()
    fake_urban_api = FakeUrbanAPI()
    dummy_producer = DummyProducer()

    handler = BaseScenarioCreatedHandler(
        renovation=fake_renovation,
        urban_api=fake_urban_api,
        producer=dummy_producer,
    )

    event = BaseScenarioCreated(
        project_id=120,
        base_scenario_id=198,
        regional_scenario_id=122,
    )

    result = await handler.handle(event, None)

    assert fake_renovation.called_with == [198]
    assert len(fake_urban_api.saved_indicators) == len(result)

    first = fake_urban_api.saved_indicators[0]["payload"]

    assert first["scenario_id"] == int(event.base_scenario_id)
    assert first["territory_id"] == 999
    assert first["hexagon_id"] is None
    assert first["information_source"] == "modeled"
    assert isinstance(first["value"], float)

    for item in fake_urban_api.saved_indicators:
        print(item["payload"])
