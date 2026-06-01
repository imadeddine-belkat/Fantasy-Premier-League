"""Merge per-season team EVENT-stats CSVs into clean combined files.

Input layout (one CSV per team per season):
    pl_stats/{Team}/events_stats/{season}_events_stats.csv

Outputs (under pl_stats/_merged_events/):
    teams/{Team}_events_stats.csv     # one per team, all seasons
    seasons/{season}_events_stats.csv  # one per season, all teams
    all_events_stats.csv               # everything, one file

Rows are per-match, so `team_dir`/`season` are injected for provenance and the
match-context columns (matchId, kickoff, opponent, ...) lead the column order;
the rest stay alphabetical. Column set may drift across seasons -> take union.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from pl import config

PL_STATS = config.OUTPUT_ROOT
MERGED = PL_STATS / "_merged" / "teams"

SEASON_RE = re.compile(r"(\d{4}-\d{2})_events_stats\.csv$")

# Match-context / identity columns surfaced first; everything else sorts after.
LEAD = [
    "team_dir", "season", "matchId", "gameweek", "kickoff", "ground",
    "attendance", "venue", "team", "opponent", "result",
]


def _read_one(csv_path: Path, team_dir: str, season: str) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return None
    if df.empty:
        return None
    df = df.drop(columns=[c for c in ("season", "team_dir") if c in df.columns])
    df.insert(0, "season", season)
    df.insert(0, "team_dir", team_dir)
    return df


def collect() -> list[tuple[str, str, pd.DataFrame]]:
    rows: list[tuple[str, str, pd.DataFrame]] = []
    for team_dir in sorted(p for p in PL_STATS.iterdir() if p.is_dir() and not p.name.startswith("_")):
        stats_dir = team_dir / "events_stats"
        if not stats_dir.is_dir():
            continue
        for csv in sorted(stats_dir.glob("*_events_stats.csv")):
            m = SEASON_RE.search(csv.name)
            if not m:
                print(f"  ? unrecognized filename, skipping: {csv}", file=sys.stderr)
                continue
            df = _read_one(csv, team_dir.name, m.group(1))
            if df is not None:
                rows.append((team_dir.name, m.group(1), df))
    return rows


def _write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lead = [c for c in LEAD if c in df.columns]
    rest = sorted(c for c in df.columns if c not in lead)
    df.to_csv(path, index=False, columns=lead + rest)


def run() -> None:
    data = collect()
    if not data:
        print("no event CSVs found under pl_stats/*/events_stats/", file=sys.stderr)
        return

    by_team: dict[str, list[pd.DataFrame]] = {}
    by_season: dict[str, list[pd.DataFrame]] = {}
    for team_dir, season, df in data:
        by_team.setdefault(team_dir, []).append(df)
        by_season.setdefault(season, []).append(df)

    for team_dir, dfs in by_team.items():
        _write(pd.concat(dfs, ignore_index=True, sort=False), MERGED / "teams" / f"{team_dir}_events_stats.csv")
    print(f"teams: {len(by_team)} files")

    for season, dfs in by_season.items():
        _write(pd.concat(dfs, ignore_index=True, sort=False), MERGED / "seasons" / f"{season}_events_stats.csv")
    print(f"seasons: {len(by_season)} files")

    everything = pd.concat([df for *_, df in data], ignore_index=True, sort=False)
    _write(everything, MERGED / "all_events_stats.csv")
    print(f"all: {len(everything)} rows -> {MERGED / 'all_events_stats.csv'}")


if __name__ == "__main__":
    run()
