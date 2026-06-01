
import logging

import pandas as pd

from fpl import config
from fpl.client import FPLClient
from fpl.http import make_session
from fpl.io import clean_filename, write_csv

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("fpl")


def main() -> None:
    client = FPLClient(make_session(), config.get_current_season())

    log.info("Fetching bootstrap-static + fixtures...")
    boot = client.bootstrap()
    season = client.current_season(boot)
    log.info("Fixtures Sync for %s", season)
    team_name = {t["id"]: clean_filename(f"{t['name']}_{t['code']}") for t in boot["teams"]}

    df = pd.DataFrame(client.fixtures()).drop(
        columns=["stats", "pulse_id"], errors="ignore"
    ).sort_values("event")

    # Combined: every fixture in one file.
    write_csv(df, config.ROOT / "fixtures" / f"{season}_all_fixtures.csv")

    log.info("Writing per-team fixtures CSVs...")
    for team_id, name in team_name.items():
        mask = (df["team_h"] == team_id) | (df["team_a"] == team_id)
        write_csv(
            df[mask],
            config.ROOT / "teams" / clean_filename(name) / "fixtures"
            / f"{season}_fixtures.csv",
        )

    log.info("Done. Wrote combined + %d per-team fixture files.", len(team_name))


if __name__ == "__main__":
    main()
