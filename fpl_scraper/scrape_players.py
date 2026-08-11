"""Sync per-team and per-player gameweek stat CSVs."""
import logging
import sys
from datetime import datetime, timezone

import requests

from fpl import config
from fpl.client import FPLClient
from fpl.http import make_session
from fpl.io import clean_filename, shape_player_rows, write_csv

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("fpl")


def finished_gameweeks(events: list[dict]) -> int:
    """Count gameweeks that are finished *and* data-checked.

    FPL flips ``finished`` before bonus points are confirmed; scraping in that
    window yields rows that change later, so we require ``data_checked`` too.
    """
    return sum(1 for e in events if e.get("finished") and e.get("data_checked"))


def next_deadline(events: list[dict]) -> str | None:
    """Deadline of the upcoming gameweek: the ``is_next`` event, else the
    earliest future ``deadline_time``. Returns None if none is in the future.
    """
    nxt = next((e for e in events if e.get("is_next")), None)
    if nxt and nxt.get("deadline_time"):
        return nxt["deadline_time"]

    now = datetime.now(timezone.utc)
    future = []
    for e in events:
        raw = e.get("deadline_time")
        if not raw:
            continue
        try:
            when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when > now:
            future.append(raw)
    return min(future) if future else None


def season_label(client: FPLClient, boot: dict) -> str:
    """Season name for messaging; falls back to the clock-derived season when
    bootstrap has no usable events (e.g. empty ``events``)."""
    try:
        return client.current_season(boot)
    except ValueError:
        return client.season


def main() -> None:
    # Clock season scopes the on-disk cache; the authoritative season label for
    # filenames comes from the API (GW1 deadline) once bootstrap is fetched.
    client = FPLClient(make_session(), config.get_current_season())

    log.info("Fetching fixtures...")
    fixture_code = client.fixture_codes()

    log.info("Fetching master player list...")
    boot = client.bootstrap()

    # Pre-flight: before GW1 is played every element-summary comes back with an
    # empty "history", so the ~577-player loop makes 4 minutes of HTTP calls and
    # writes nothing. Skip the whole run until at least one gameweek has both
    # finished and had its data checked. Exit 0 so the Actions job stays green.
    events = boot.get("events") or []
    finished_gws = finished_gameweeks(events)
    if finished_gws == 0:
        season = season_label(client, boot)
        deadline = next_deadline(events) or "unknown (no upcoming deadline in bootstrap)"
        log.info(
            "No finished gameweeks for %s yet (next deadline: %s). "
            "Skipping player sync — nothing to scrape pre-season.",
            season, deadline,
        )
        sys.exit(0)

    season = client.current_season(boot)
    log.info("Players Sync for %s", season)
    players_meta = boot["elements"]
    team_dir_name = {t["id"]: clean_filename(f"{t['name']}_{t['code']}") for t in boot["teams"]}
    positions = {et["id"]: et["singular_name_short"] for et in boot["element_types"]}
    log.info("Processing %d players...", len(players_meta))

    team_rows: dict[int, list[dict]] = {}
    player_rows: dict[str, list[dict]] = {}

    for i, p in enumerate(players_meta):
        try:
            payload = client.player_summary(p["id"])
        except requests.RequestException:
            log.warning("    Skipping %s after retries", p["id"])
            continue

        history = (payload or {}).get("history", [])
        if not history:
            continue

        folder = clean_filename(f"{p['first_name']}_{p['second_name']}_{p['code']}")
        for gw in history:
            gw["player_code"] = p["code"]
            gw["position"] = positions.get(p["element_type"])
            gw["first_name"] = p["first_name"]
            gw["second_name"] = p["second_name"]
            gw["team_code"] = p["team_code"]
            # history row's 'fixture' is the fixture id; map to its code
            gw["fixture_code"] = fixture_code.get(gw.get("fixture"))
            team_rows.setdefault(p["team"], []).append(gw)
            player_rows.setdefault(folder, []).append(gw)

        if (i + 1) % 100 == 0:
            log.info(" Progress: %d/%d...", i + 1, len(players_meta))

    log.info("Writing per-team player CSVs...")
    for team_id, rows in team_rows.items():
        write_csv(
            shape_player_rows(rows),
            config.ROOT / "teams" / team_dir_name[team_id] / "players"
            / f"{season}_all_players_gw.csv",
        )

    log.info("Writing per-player CSVs...")
    for folder, rows in player_rows.items():
        write_csv(
            shape_player_rows(rows),
            config.ROOT / "players" / folder / f"{season}_gw_stats.csv",
        )

    log.info(
        "Players sync complete! Wrote %d team files, %d player files.",
        len(team_rows), len(player_rows),
    )


if __name__ == "__main__":
    main()