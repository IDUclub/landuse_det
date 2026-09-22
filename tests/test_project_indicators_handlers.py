import pytest
from otteroad.models.scenario_events.projects.BaseScenarioCreated import BaseScenarioCreated
from otteroad.models.scenario_events.projects.ProjectCreated import ProjectCreated
from otteroad.models.scenario_events.projects.ScenarioZonesUpdated import (
    ScenarioZonesUpdated,
)

from landuse_app.auth_context import (
    get_current_bearer_token,
    in_service_scope,
    reset_current_bearer_token,
    set_current_bearer_token,
)
from landuse_app.broker_handlers.base_scenario_created_handler import (
    BaseScenarioCreatedHandler,
)
from landuse_app.broker_handlers.project_created_handler import ProjectCreatedHandler
from landuse_app.broker_handlers.project_indicators import ProjectIndicatorsRecalculator
from landuse_app.broker_handlers.scenario_zones_updated_handler import (
    ScenarioZonesUpdatedHandler,
)
from landuse_app.logic.api.urban_db_api_client import RequestHandler


class FakeRenovation:
    def __init__(self):
        self.calls = []

    async def calculate_zone_percentages(self, scenario_id: int) -> dict:
        self.calls.append((scenario_id, get_current_bearer_token(), in_service_scope()))
        return {"Земли жилой застройки": 40.0, "Неизвестная категория": 1.0}


class FakeIndicators:
    def __init__(self, fail: bool = False):
        self.calls = []
        self.fail = fail

    async def calculate_project_territory_area(self, project_id, force_recalculate=False):
        self.calls.append((project_id, force_recalculate, in_service_scope()))
        if self.fail:
            raise RuntimeError("urban api down")


class FakeUrbanApi:
    def __init__(self):
        self.puts = []

    async def put_project_indicator(self, scenario_id, payload, **kwargs):
        self.puts.append((scenario_id, payload))


def make_recalculator(indicators_fail: bool = False):
    renovation, indicators, urban_api = FakeRenovation(), FakeIndicators(indicators_fail), FakeUrbanApi()
    return ProjectIndicatorsRecalculator(renovation, urban_api, indicators), renovation, indicators, urban_api


@pytest.mark.asyncio
async def test_project_created_saves_area_and_zone_balance():
    rec, renovation, indicators, urban_api = make_recalculator()

    await ProjectCreatedHandler(rec).handle(
        ProjectCreated(project_id=139, base_scenario_id=250, territory_id=1)
    )

    assert indicators.calls == [(139, True, True)]
    assert [s for s, *_ in renovation.calls] == [250]
    assert urban_api.puts == [
        (
            250,
            {
                "indicator_id": 17,
                "scenario_id": 250,
                "territory_id": None,
                "hexagon_id": None,
                "value": 40.0,
                "comment": "--",
                "information_source": "landuse_det",
                "properties": {},
            },
        )
    ]


@pytest.mark.asyncio
async def test_project_created_zone_balance_runs_even_if_area_fails():
    rec, renovation, _, urban_api = make_recalculator(indicators_fail=True)

    await ProjectCreatedHandler(rec).handle(
        ProjectCreated(project_id=139, base_scenario_id=250, territory_id=1)
    )

    assert len(renovation.calls) == 1
    assert len(urban_api.puts) == 1


@pytest.mark.asyncio
async def test_scenario_zones_updated_recalculates_zone_balance_only():
    rec, renovation, indicators, urban_api = make_recalculator()

    await ScenarioZonesUpdatedHandler(rec).handle(
        ScenarioZonesUpdated(project_id=139, scenario_id=777)
    )

    assert indicators.calls == []
    assert [s for s, *_ in renovation.calls] == [777]
    assert urban_api.puts[0][0] == 777


@pytest.mark.asyncio
async def test_base_scenario_created_still_handled():
    rec, renovation, indicators, _ = make_recalculator()

    await BaseScenarioCreatedHandler(rec).handle(
        BaseScenarioCreated(project_id=139, base_scenario_id=250, regional_scenario_id=151)
    )

    assert len(indicators.calls) == 1
    assert len(renovation.calls) == 1


@pytest.mark.asyncio
async def test_service_scope_drops_user_token_and_restores_it():
    rec, renovation, _, _ = make_recalculator()
    marker = set_current_bearer_token("user-token")
    try:
        await rec.recalculate_zone_balance(250)
        assert get_current_bearer_token() == "user-token"
        assert not in_service_scope()
    finally:
        reset_current_bearer_token(marker)

    assert renovation.calls == [(250, None, True)]


class FakeAuth:
    def __init__(self):
        self.refreshes = 0

    async def get_token(self, *, force_refresh: bool = False) -> str:
        if force_refresh:
            self.refreshes += 1
            return "fresh-service-token"
        return "service-token"


class FakeCache:
    def __init__(self):
        self.lookups = 0

    def get_recent_cache_file(self, key, params):
        self.lookups += 1
        return None

    def save_with_cleanup(self, *args):
        pass


@pytest.mark.asyncio
async def test_request_handler_uses_service_token_and_skips_cache_in_service_scope(monkeypatch):
    from landuse_app.auth_context import service_scope

    cache = FakeCache()
    handler = RequestHandler("http://urban", FakeAuth(), cache)
    seen = {}

    class FakeResp:
        status = 200

        async def json(self):
            return {"ok": True}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def get(self, url, params=None, headers=None):
            seen["headers"] = headers
            return FakeResp()

    monkeypatch.setattr("landuse_app.logic.api.urban_db_api_client.aiohttp.ClientSession", FakeSession)

    with service_scope():
        assert await handler.get("/api/v1/projects/1/territory") == {"ok": True}
    assert seen["headers"]["Authorization"] == "Bearer service-token"
    assert cache.lookups == 0

    await handler.get("/api/v1/projects/1/territory")
    assert cache.lookups == 1


class ScriptedSession:
    """aiohttp.ClientSession stub replying with a scripted list of statuses."""

    def __init__(self, statuses, seen):
        self.statuses, self.seen = statuses, seen

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _reply(self, headers):
        self.seen.append(headers["Authorization"])
        status = self.statuses.pop(0)

        class Resp:
            async def json(self_inner):
                return {"ok": True}

            async def text(self_inner):
                return "unauthorized"

            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *exc):
                return False

        resp = Resp()
        resp.status = status
        return resp

    def get(self, url, params=None, headers=None):
        return self._reply(headers)

    def put(self, url, json=None, headers=None):
        return self._reply(headers)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "put"])
async def test_service_token_refreshed_once_on_401(monkeypatch, method):
    from fastapi import HTTPException

    from landuse_app.auth_context import service_scope

    auth, seen = FakeAuth(), []
    handler = RequestHandler("http://urban", auth, FakeCache())
    monkeypatch.setattr(
        "landuse_app.logic.api.urban_db_api_client.aiohttp.ClientSession",
        ScriptedSession([401, 200], seen),
    )
    with service_scope():
        assert await getattr(handler, method)("/api/v1/x") == {"ok": True}
    assert seen == ["Bearer service-token", "Bearer fresh-service-token"]
    assert auth.refreshes == 1

    # A second 401 after refresh is a real permission error: no refresh loop.
    monkeypatch.setattr(
        "landuse_app.logic.api.urban_db_api_client.aiohttp.ClientSession",
        ScriptedSession([401, 401], []),
    )
    with service_scope(), pytest.raises(HTTPException) as exc:
        await getattr(handler, method)("/api/v1/x")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_user_token_401_is_not_retried_with_service_token(monkeypatch):
    from fastapi import HTTPException

    auth, seen = FakeAuth(), []
    handler = RequestHandler("http://urban", auth, None)
    monkeypatch.setattr(
        "landuse_app.logic.api.urban_db_api_client.aiohttp.ClientSession",
        ScriptedSession([401], seen),
    )
    marker = set_current_bearer_token("user-token")
    try:
        with pytest.raises(HTTPException) as exc:
            await handler.get("/api/v1/x")
    finally:
        reset_current_bearer_token(marker)
    assert exc.value.status_code == 401
    assert seen == ["Bearer user-token"]
    assert auth.refreshes == 0


@pytest.mark.asyncio
async def test_keycloak_error_mapped_to_503():
    from fastapi import HTTPException
    from idu_service_auth import TokenRequestError

    from landuse_app.logic.api.urban_db_api_client import AuthService

    class BrokenClient:
        async def get_access_token(self, *, force_refresh=False):
            raise TokenRequestError("keycloak down")

    auth = AuthService.__new__(AuthService)
    auth._client = BrokenClient()
    with pytest.raises(HTTPException) as exc:
        await auth.get_token()
    assert exc.value.status_code == 503
