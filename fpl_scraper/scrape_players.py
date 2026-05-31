"""Sync per-team and per-player gameweek stat CSVs."""
import logging

import requests

from fpl import config
from fpl.client import FPLClient
from fpl.http import make_session
from fpl.io import clean_filename, shape_player_rows, write_csv

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("fpl")


def main() -> None:
    season = config.get_current_season()
    log.info("Starting Players Sync for %s", season)

    client = FPLClient(make_session(), season)

    log.info("Fetching fixtures...")
    fixture_code = client.fixture_codes()

    log.info("Fetching master player list...")
    boot = client.bootstrap()
    players_meta = boot["elements"]
    team_dir_name = {t["id"]: clean_filename(f"{t['name']}_{t['code']}") for t in boot["teams"]}
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
            gw["first_name"] = p["first_name"]
            gw["second_name"] = p["second_name"]
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

    log.info("Writing season-wide player index...")
    all_rows = [row for rows in player_rows.values() for row in rows]
    write_csv(
        shape_player_rows(all_rows),
        config.ROOT / "_index" / "players" / f"{season}_all_players_gw.csv",
    )

    log.info(
        "Players sync complete! Wrote %d team files, %d player files.",
        len(team_rows), len(player_rows),
    )


if __name__ == "__main__":
    main()