"""Configuration: paths, constants, and season resolution."""
from datetime import datetime
from pathlib import Path

BASE_URL = "https://fantasy.premierleague.com/api/"

ROOT = Path("fpl_stats")
CACHE_DIR = Path("fpl_cache")

# Politeness delay (seconds) after a real network hit to element-summary.
PLAYER_FETCH_DELAY = 0.3

# Columns on a player-history row that duplicate fixture data living in the
# fixtures CSV. Dropped on write; fixture_code is the only join key kept.
FIXTURE_DERIVED_COLS = [
    "fixture", "opponent_team", "was_home", "kickoff_time",
    "team_h_score", "team_a_score", "round",
]

# Identity + join key ordered first; remaining stat columns follow in API order.
PLAYER_LEAD_COLS = ["element", "player_code", "first_name", "second_name", "fixture_code"]


def get_current_season(now: datetime | None = None) -> str:
    """Return season string like '2025-26'. Season rolls over in August."""
    now = now or datetime.now()
    if now.month >= 8:
        return f"{now.year}-{str(now.year + 1)[2:]}"
    return f"{now.year - 1}-{str(now.year)[2:]}"