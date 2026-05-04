"""Constants for Fotbollstabeller integration (fotbollstabeller.nu)."""

DOMAIN = "fotbollstabeller"
CONF_GROUP_URL = "group_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 3600  # seconds (1 hour)

BASE_URL = "https://www.fotbollstabeller.nu"

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

# Known leagues from fotbollstabeller.nu
KNOWN_LEAGUES = [
    # ── Toppen ─────────────────────────────────────────
    {"name": "Allsvenskan (Herrar)", "slug": "allsvenskan-herrar"},
    {"name": "Superettan (Herrar)", "slug": "superettan-herrar"},
    {"name": "Allsvenskan (Damer)", "slug": "allsvenskan-damer"},
    {"name": "Elitettan (Damer)", "slug": "elitettan-damer"},
    # ── Division 1 ────────────────────────────────────
    {"name": "Ettan Norra (Herrar)", "slug": "division-1-norra-herrar"},
    {"name": "Ettan Södra (Herrar)", "slug": "division-1-sodra-herrar"},
    {"name": "Division 1 Norra (Damer)", "slug": "division-1-norra-damer"},
    {"name": "Division 1 Mellersta (Damer)", "slug": "division-1-mellersta-damer"},
    {"name": "Division 1 Södra (Damer)", "slug": "division-1-sodra-damer"},
    # ── Division 2 ────────────────────────────────────
    {"name": "Division 2 Norrland Norra (Herrar)", "slug": "division-2-norrland-herrar"},
    {"name": "Division 2 Norrland Södra (Herrar)", "slug": "division-2-norrland-sodra-herrar"},
    {"name": "Division 2 Norra Svealand (Herrar)", "slug": "division-2-norra-svealand-herrar"},
    {"name": "Division 2 Södra Svealand (Herrar)", "slug": "division-2-sodra-svealand-herrar"},
    {"name": "Division 2 Norra Götaland (Herrar)", "slug": "division-2-norra-gotaland-herrar"},
    {"name": "Division 2 Västra Götaland (Herrar)", "slug": "division-2-vastra-gotaland-herrar"},
    {"name": "Division 2 Södra Götaland (Herrar)", "slug": "division-2-sodra-gotaland-herrar"},
    # ── Division 3 ────────────────────────────────────
    {"name": "Division 3 Mellersta Norrland (Herrar)", "slug": "division-3-mellersta-norrland-herrar"},
    {"name": "Division 3 Södra Norrland (Herrar)", "slug": "division-3-sodra-norrland-herrar"},
    {"name": "Division 3 Norra Svealand (Herrar)", "slug": "division-3-norra-svealand-herrar"},
    {"name": "Division 3 Södra Svealand (Herrar)", "slug": "division-3-sodra-svealand-herrar"},
    {"name": "Division 3 Mellersta Svealand (Herrar)", "slug": "division-3-mellersta-svealand-herrar"},
    {"name": "Division 3 Nordöstra Götaland (Herrar)", "slug": "division-3-nordostra-gotaland-herrar"},
    {"name": "Division 3 Nordvästra Götaland (Herrar)", "slug": "division-3-nordvastra-gotaland-herrar"},
    {"name": "Division 3 Mellersta Götaland (Herrar)", "slug": "division-3-mellersta-gotaland-herrar"},
    {"name": "Division 3 Sydöstra Götaland (Herrar)", "slug": "division-3-sydostra-gotaland-herrar"},
    {"name": "Division 3 Sydvästra Götaland (Herrar)", "slug": "division-3-sydvastra-gotaland-herrar"},
    {"name": "Division 3 Södra Götaland (Herrar)", "slug": "division-3-sodra-gotaland-herrar"},
    # ── Juniorer ──────────────────────────────────────
    {"name": "P17 Allsvenskan Norra", "slug": "u17-allsvenskan-norra"},
    {"name": "P17 Allsvenskan Södra", "slug": "u17-allsvenskan-sodra"},
    {"name": "P19 Allsvenskan", "slug": "u19-allsvenskan"},
    {"name": "P19 Superettan Norra", "slug": "p19-superettan-norra"},
    {"name": "P19 Superettan Södra", "slug": "p19-superettan-sodra"},
    {"name": "F17 Allsvenskan Norra", "slug": "f17-allsvenskan-norra"},
    {"name": "F17 Allsvenskan Södra", "slug": "f17-allsvenskan-sodra"},
    {"name": "F19 Allsvenskan", "slug": "f-19-allsvenskan"},
]
