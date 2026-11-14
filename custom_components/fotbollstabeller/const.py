"""Constants for Fotbollstabeller integration."""

DOMAIN = "fotbollstabeller"
CONF_GROUP_URL = "group_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 14400  # seconds (4 hours)

BASE_URL = "https://www.thesportsdb.com/api/v1/json"
DEFAULT_API_KEY = "123"

ATTR_POSITION = "position"
ATTR_TEAM = "team"
ATTR_PLAYED = "played_games"
ATTR_WON = "won"
ATTR_DRAW = "draw"
ATTR_LOST = "lost"
ATTR_GOALS_FOR = "goals_for"
ATTR_GOALS_AGAINST = "goals_against"
ATTR_GOAL_DIFFERENCE = "goal_difference"
ATTR_POINTS = "points"
ATTR_TABLE = "standings"

# Available Swedish leagues from SportsDB.
KNOWN_LEAGUES = [
    {"name": "Swedish Allsvenskan", "slug": "allsvenskan"},
    {"name": "Sweden Damallsvenskan", "slug": "damallsvenskan"},
    {"name": "Svenska Cupen", "slug": "svenska-cupen"},
    {"name": "Swedish Division 1 North", "slug": "ettan-norra"},
    {"name": "Swedish Division 1 South", "slug": "ettan-sodra"},
]
