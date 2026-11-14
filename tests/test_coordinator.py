import asyncio
import importlib.util
import os
import sys
import types
import unittest

# Stub Home Assistant and third-party dependencies so the parser can be imported in isolation.
homeassistant = types.ModuleType("homeassistant")
core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
helpers = types.ModuleType("homeassistant.helpers")
update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
class DataUpdateCoordinator:  # pragma: no cover - simple stub
    pass
class UpdateFailed(Exception):
    pass
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
helpers.update_coordinator = update_coordinator
aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
aiohttp_client.async_get_clientsession = lambda hass: None
config_validation = types.ModuleType("homeassistant.helpers.config_validation")
config_validation.config_entry_only_config_schema = lambda *args, **kwargs: None
storage = types.ModuleType("homeassistant.helpers.storage")
class Store:  # pragma: no cover - simple stub
    def __init__(self, *args, **kwargs):
        pass
    async def async_load(self):
        return None
    async def async_save(self, data):
        pass
storage.Store = Store
components = types.ModuleType("homeassistant.components")
websocket_api = types.ModuleType("homeassistant.components.websocket_api")
websocket_api.websocket_command = lambda *args, **kwargs: (lambda func: func)
websocket_api.async_response = lambda func: func
websocket_api.ActiveConnection = object
websocket_api.async_register_command = lambda *args, **kwargs: None
frontend = types.ModuleType("homeassistant.components.frontend")
frontend.add_extra_js_url = lambda *args, **kwargs: None
config_entries = types.ModuleType("homeassistant.config_entries")
config_entries.ConfigEntry = object

voluptuous = types.ModuleType("voluptuous")
class _Required:
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return None
voluptuous.Required = _Required
voluptuous.Optional = _Required
voluptuous.Schema = lambda *args, **kwargs: None

aiohttp = types.ModuleType("aiohttp")
aiohttp.ClientSession = object
aiohttp.ClientTimeout = lambda *args, **kwargs: None

for name, module in {
    "homeassistant": homeassistant,
    "homeassistant.core": core,
    "homeassistant.helpers": helpers,
    "homeassistant.helpers.update_coordinator": update_coordinator,
    "homeassistant.helpers.aiohttp_client": aiohttp_client,
    "homeassistant.helpers.config_validation": config_validation,
    "homeassistant.helpers.storage": storage,
    "homeassistant.components": components,
    "homeassistant.components.websocket_api": websocket_api,
    "homeassistant.components.frontend": frontend,
    "homeassistant.config_entries": config_entries,
    "voluptuous": voluptuous,
    "aiohttp": aiohttp,
}.items():
    sys.modules[name] = module

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [os.path.join(ROOT, "custom_components")]
sys.modules["custom_components"] = custom_components_pkg

fotbollstabeller_pkg = types.ModuleType("custom_components.fotbollstabeller")
fotbollstabeller_pkg.__path__ = [os.path.join(ROOT, "custom_components", "fotbollstabeller")]
sys.modules["custom_components.fotbollstabeller"] = fotbollstabeller_pkg

spec = importlib.util.spec_from_file_location(
    "custom_components.fotbollstabeller.coordinator",
    os.path.join(ROOT, "custom_components", "fotbollstabeller", "coordinator.py"),
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
_parse_standings = module._parse_standings


class ParseStandingsTest(unittest.TestCase):
    def test_parse_new_page_table(self):
        html = '''
        SÄSONGEN 2026
        | 1 | Hammarby | 28 | 18 | 4 | 6 | +37 | 58 |
        | 2 | IK Sirius | 28 | 18 | 4 | 6 | +23 | 58 |
        '''

        rows = _parse_standings(html)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["team"], "Hammarby")
        self.assertEqual(rows[0]["points"], 58)
        self.assertEqual(rows[1]["goal_difference"], 23)

    def test_sportsdb_league_id_resolution(self):
        league_id = module._resolve_league_id("allsvenskan")
        self.assertEqual(league_id, "4347")

        result = module._normalize_sportsdb_table([
            {
                "intRank": "1",
                "strTeam": "Hammarby",
                "intPlayed": "28",
                "intWin": "18",
                "intDraw": "4",
                "intLoss": "6",
                "intGoalsFor": "60",
                "intGoalsAgainst": "23",
                "intGoalDifference": "37",
                "intPoints": "58",
                "strBadge": "https://example.com/logo.png",
            }
        ])

        self.assertEqual(result[0]["team"], "Hammarby")
        self.assertEqual(result[0]["points"], 58)
        self.assertEqual(result[0]["team_logo"], "https://example.com/logo.png")

    def test_fetch_standings_accepts_api_key(self):
        class DummyResponse:
            status = 200
            async def json(self):
                return {"table": [{
                    "intRank": "1",
                    "strTeam": "Hammarby",
                    "intPlayed": "28",
                    "intWin": "18",
                    "intDraw": "4",
                    "intLoss": "6",
                    "intGoalsFor": "60",
                    "intGoalsAgainst": "23",
                    "intGoalDifference": "37",
                    "intPoints": "58",
                    "strBadge": "https://example.com/logo.png",
                }]}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class DummySession:
            def get(self, url, headers=None, timeout=None):
                self.url = url
                self.headers = headers
                return DummyResponse()

        session = DummySession()
        name, rows = asyncio.run(module.fetch_standings(session, "allsvenskan", api_key="custom123"))
        self.assertEqual(name, "Swedish Allsvenskan")
        self.assertEqual(rows[0]["team"], "Hammarby")
        self.assertIn("custom123", session.url)


if __name__ == "__main__":
    unittest.main()
