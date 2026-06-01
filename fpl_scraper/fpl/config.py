"""Configuration: paths, constants, and season resolution."""
from datetime import datetime
from pathlib import Path

BASE_URL = "https://fantasy.premierleague.com/api/"

ROOT = Path("fpl_stats")
CACHE_DIR = Path("fpl_cache")

PLAYER_FETCH_DELAY = 0.3

FIXTURE_DERIVED_COLS = [
    "fixture", "opponent_team", "was_home", "kickoff_time",
    "team_h_score", "team_a_score", "round",
]

PLAYER_LEAD_COLS = ["element", "player_code", "first_name", "second_name", "fixture_code"]


def get_current_season(now: datetime | None = None) -> str:
    now = now or datetime.now()
    if now.month >= 8:
        return f"{now.year}-{str(now.year + 1)[2:]}"
    return f"{now.year - 1}-{str(now.year)[2:]}"


def season_from_bootstrap(boot: dict) -> str:
    events = boot.get("events") or []
    gw1 = next((e for e in events if e.get("id") == 1), events[0] if events else None)
    deadline = (gw1 or {}).get("deadline_time")
    if not deadline:
        raise ValueError("cannot derive season: no GW1 deadline_time in bootstrap")
    start_year = datetime.fromisoformat(deadline.replace("Z", "+00:00")).year
    return f"{start_year}-{str(start_year + 1)[2:]}"