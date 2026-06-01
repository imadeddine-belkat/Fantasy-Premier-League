from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from fpl import config
from fpl.client import FPLClient
from fpl.http import make_session

ROOT = Path(__file__).resolve().parent / config.ROOT
INDEX_DIR = ROOT / "_index"
TEAM_INDEX = INDEX_DIR / "_teams_index.json"
PLAYER_INDEX = INDEX_DIR / "_players_index.json"

_PLAYER_SEASON_RE = re.compile(r"(\d{4}-\d{2})_all_players_gw\.csv$")


def _int_or_none(v) -> int | None:
    s = str(v or "").strip()
    return int(s) if s.isdigit() else None


def _nest_sorted(acc: dict[int, dict[str, dict]]) -> dict[str, dict]:
    return {
        str(code): {s: acc[code][s] for s in sorted(acc[code])}
        for code in sorted(acc)
    }


def _load_existing(path: Path) -> dict[int, dict[str, dict]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {int(code): seasons for code, seasons in data.items()}


def build_player_index() -> dict[str, dict]:
    acc: dict[int, dict[str, dict]] = {}
    csv_paths = sorted(ROOT.glob("teams/*/players/*_all_players_gw.csv"))
    if not csv_paths:
        print(f"  ! no per-team player CSVs under {ROOT / 'teams'} "
              f"(run scrape_players.py first) — player index will be empty")

    for path in csv_paths:
        sm = _PLAYER_SEASON_RE.search(path.name)
        if not sm:
            continue
        season = sm.group(1)
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                code = (row.get("player_code") or "").strip()
                name = f"{(row.get('first_name') or '').strip()} {(row.get('second_name') or '').strip()}".strip()
                if not (code.isdigit() and name):
                    continue
                acc.setdefault(int(code), {})[season] = {
                    "element": _int_or_none(row.get("element")),
                    "name": name,
                }

    print(f"players: {len(acc)} unique codes across {len({p.parent for p in csv_paths})} team dir(s)")
    return _nest_sorted(acc)


def build_team_index() -> dict[str, dict]:
    acc = _load_existing(TEAM_INDEX)

    client = FPLClient(make_session(), config.get_current_season())
    boot = client.bootstrap()
    season = client.current_season(boot)
    for t in boot["teams"]:
        code = _int_or_none(t.get("code"))
        name = (t.get("name") or "").strip()
        if code is None or not name:
            continue
        acc.setdefault(code, {})[season] = {
            "id": _int_or_none(t.get("id")),
            "name": name,
            "short_name": (t.get("short_name") or "").strip() or None,
        }

    print(f"teams: {len(acc)} unique codes (current season {season} refreshed)")
    return _nest_sorted(acc)


def _write(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"-> wrote {len(data)} entries to {path}")


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    _write(build_team_index(), TEAM_INDEX)
    _write(build_player_index(), PLAYER_INDEX)


if __name__ == "__main__":
    main()