"""Sync per-team fixtures CSVs."""
import logging

import pandas as pd

from fpl import config
from fpl.client import FPLClient
from fpl.http import make_session
from fpl.io import clean_filename, write_csv

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("fpl")


def main() -> None:
    season = config.get_current_season()
    log.info("Starting Teams Fixtures Sync for %s", season)

    client = FPLClient(make_session(), season)

    log.info("Fetching bootstrap-static + fixtures...")
    boot = client.bootstrap()
    team_name = {t["id"]: clean_filename(f"{t['name']}_{t['code']}") for t in boot["teams"]}

    df = pd.DataFrame(client.fixtures()).drop(
        columns=["stats", "pulse_id"], errors="ignore"
    )

    # Whole fixtures table -> players
    write_csv(
        df.sort_values("event"),
        config.ROOT / "players" / "fixtures" / f"{season}_all_fixtures.csv",
    )

    log.info("Writing per-team fixtures CSVs...")
    for team_id, name in team_name.items():
        mask = (df["team_h"] == team_id) | (df["team_a"] == team_id)
        write_csv(
            df[mask].sort_values("event"),
            config.ROOT / "teams" / clean_filename(name) / "fixtures"
            / f"{season}_fixtures.csv",
        )

    log.info("Done. Wrote fixtures for %d teams.", len(team_name))


if __name__ == "__main__":
    main()