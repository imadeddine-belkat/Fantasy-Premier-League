"""Merge per-team player GW CSVs into one file per season."""
import csv
import re
from pathlib import Path
from collections import defaultdict
from fpl import config

BASE = config.ROOT / "teams"
OUT = config.ROOT / "_merged" / "players"
PATTERN = re.compile(r"^(?P<season>.+)_all_players_gw\.csv$")


def merge():
    OUT.mkdir(parents=True, exist_ok=True)
    # season -> list of source CSV paths
    by_season = defaultdict(list)

    for team_dir in sorted(BASE.iterdir()):
        players_dir = team_dir / "players"
        if not players_dir.is_dir():
            continue
        for csv_path in sorted(players_dir.glob("*_all_players_gw.csv")):
            m = PATTERN.match(csv_path.name)
            if m:
                by_season[m.group("season")].append(csv_path)

    for season, paths in sorted(by_season.items()):
        out_path = OUT / f"{season}_all_players_gw.csv"
        header_written = False
        rows = 0
        with out_path.open("w", newline="", encoding="utf-8") as out_f:
            writer = None
            for p in paths:
                with p.open(newline="", encoding="utf-8") as in_f:
                    reader = csv.reader(in_f)
                    header = next(reader, None)
                    if header is None:
                        continue
                    if not header_written:
                        writer = csv.writer(out_f)
                        writer.writerow(header)  # write header once from first file
                        header_written = True
                    for row in reader:
                        writer.writerow(row)
                        rows += 1
        print(f"{season}: {len(paths)} teams -> {rows} rows -> {out_path}")


if __name__ == "__main__":
    merge()