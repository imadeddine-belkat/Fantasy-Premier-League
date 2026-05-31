"""Filesystem + dataframe shaping helpers."""
import re
from pathlib import Path

import pandas as pd

from . import config


def clean_filename(name) -> str:
    return re.sub(r"(?u)[^-\w.]", "", str(name).strip().replace(" ", "_"))


def shape_player_rows(rows: list[dict]) -> pd.DataFrame:
    """Drop fixture-derived columns and order identity/join keys first."""
    df = pd.DataFrame(rows).drop(columns=config.FIXTURE_DERIVED_COLS, errors="ignore")
    lead = [c for c in config.PLAYER_LEAD_COLS if c in df.columns]
    return df[lead + [c for c in df.columns if c not in lead]]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)