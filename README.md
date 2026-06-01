# ⚽ Premier League Stats

> A unified data repository combining live **Fantasy Premier League (FPL)** statistics for the 2025-26 season with a **historical Premier League archive** spanning 2008-09 to the present.

[![FPL API](https://img.shields.io/badge/FPL-Official%20API-37003C)](https://fantasy.premierleague.com/api/)
[![PL Data](https://img.shields.io/badge/Historical-PulseLive%20API-360D3A)](https://www.premierleague.com/)
[![Automation](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Format](https://img.shields.io/badge/format-CSV-150458?logo=pandas&logoColor=white)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Dataset Reference](#dataset-reference)
  - [1. FPL — Per-Player Gameweeks](#1-fpl--per-player-gameweeks)
  - [2. FPL — Per-Team Gameweeks & Fixtures](#2-fpl--per-team-gameweeks--fixtures)
  - [3. FPL — Cross-Entity Index](#3-fpl--cross-entity-index)
  - [4. Historical PL Archive](#4-historical-pl-archive)
- [Data Design Philosophy](#data-design-philosophy)
- [Update Cadence](#update-cadence)
- [Getting Started](#getting-started)
- [Use Cases](#use-cases)
- [Data Caveats](#data-caveats)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This repository serves two complementary purposes, each with its own scraper and data tree.

| Component | Source | Scraper | Coverage |
| :--- | :--- | :--- | :--- |
| **Active FPL Scraper** | Official FPL API (`bootstrap-static`, `fixtures`, `element-summary`) | `fpl_scraper/` | 2025-26 |
| **Historical PL Archive** | Premier League PulseLive API | `pl_scraper/` | 2008-09 → present |

The FPL pipeline is fully automated via GitHub Actions. The historical PL archive is generated locally and committed as CSV — see [Update Cadence](#update-cadence) for why. All output is analysis-ready CSV that drops straight into Pandas, R, Tableau, or Power BI.

---

## Repository Structure

```
Premier-League-Stats/
├── fpl_scraper/                          # FPL pipeline (automated)
│   ├── fpl/                              # Reusable package
│   │   ├── config.py                     # Paths, season resolution, column policy
│   │   ├── http.py                       # Session + retry/backoff
│   │   ├── client.py                     # FPL API client (bootstrap, fixtures, summaries)
│   │   └── io.py                         # Row shaping + CSV writing
│   ├── scrape_players.py                 # Per-player + per-team gameweek CSVs
│   ├── scrape_teams.py                   # Team-level + fixtures CSVs
│   └── fpl_stats/                        # ← FPL output lives here
│       ├── players/
│       │   └── {First_Last}_{element_code}/
│       │       └── {season}_gw_stats.csv
│       ├── teams/
│       │   └── {Team}_{code}/
│       │       ├── players/{season}_all_players_gw.csv
│       │       └── fixtures/{season}_fixtures.csv
│       └── _index/
│           ├── players/{season}_all_players_gw.csv   # every player row, flattened
│           └── fixtures/{season}_all_fixtures.csv
│
├── pl_stats/                             # Historical PL archive, by club
│   └── {Team}_{code}/
│       ├── events_stats/{season}_events_stats.csv     # per-match team event stats
│       ├── players_stats/{season}_players_stats.csv   # per-player season aggregates
│       └── squad/{season}_squad.csv                   # squad list + bios
│   ├── _badges/{team_code}.svg            # club crest assets
│   ├── _index/_index.json                 # team code → canonical name map
│   └── _merged/                           # combined views (generated)
│       └── teams/
│           ├── teams/{Team}_events_stats.csv      # one file per club, all seasons
│           ├── seasons/{season}_events_stats.csv   # one file per season, all clubs
│           └── all_events_stats.csv                # everything, one file
│
├── .github/workflows/
│   └── fpl_updater.yml                    # Weekly FPL scrape + auto-commit
├── requirements.txt
└── README.md
```

> **Note:** The scraping logic for the historical `pl_stats/` archive (the `pl/` package and its PulseLive client) is run locally and is not committed — only the resulting CSVs are. `pl_scraper/merge_events.py` imports `from pl import config`, so it expects that package to be present locally.

---

## Dataset Reference

### 1. FPL — Per-Player Gameweeks
One CSV per player, tracking every gameweek of the current season.

| Field | Value |
| :--- | :--- |
| **Path** | `fpl_scraper/fpl_stats/players/{First_Last}_{element_code}/{season}_gw_stats.csv` |
| **Granularity** | One row per player per gameweek appearance |
| **Join key** | `fixture_code` — links to the matching row in any `fixtures` CSV |

**Columns:** `element`, `player_code`, `first_name`, `second_name`, `fixture_code`, then every FPL stat field as-is: `total_points`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `bonus`, `bps`, `influence`, `creativity`, `threat`, `ict_index`, the defensive block (`clearances_blocks_interceptions`, `recoveries`, `tackles`, `defensive_contribution`), the expected block (`expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded`), and price/ownership (`value`, `selected`, `transfers_in`, `transfers_out`, `transfers_balance`). A `modified` flag marks rows the API may revise post-deadline.

### 2. FPL — Per-Team Gameweeks & Fixtures
| File | Contents |
| :--- | :--- |
| `teams/{Team}_{code}/players/{season}_all_players_gw.csv` | Every gameweek row for that club's players, same schema as above |
| `teams/{Team}_{code}/fixtures/{season}_fixtures.csv` | Raw fixture rows: `code`, `event`, `kickoff_time`, `team_h`/`team_a`, scores, `team_h_difficulty`/`team_a_difficulty` (FDR), status flags |

### 3. FPL — Cross-Entity Index
Flattened global tables for whole-league analysis without walking the per-team tree.

| File | Contents |
| :--- | :--- |
| `_index/players/{season}_all_players_gw.csv` | All players' gameweek rows in one table |
| `_index/fixtures/{season}_all_fixtures.csv` | The full fixture list / FDR table |

### 4. Historical PL Archive (`pl_stats/`)
Club-by-club PulseLive data for 40+ current and historic top-flight clubs — including past spells from Blackpool, Bolton, Portsmouth, and others. Each club directory only contains seasons in which it actually played in the Premier League.

| File | Contents |
| :--- | :--- |
| `events_stats/{season}_events_stats.csv` | Per-match team event data (~70 columns: xG, passing, duels, set pieces, defensive actions) |
| `players_stats/{season}_players_stats.csv` | Per-player season aggregates (~110 columns) |
| `squad/{season}_squad.csv` | Squad list with bios: position, nationality, DOB, height/weight, loan status |
| `_merged/teams/all_events_stats.csv` | All clubs × all seasons of event stats, one file (built by `merge_events.py`) |

---

## Data Design Philosophy

The FPL scraper follows a strict **raw-data-only** policy:

- **No derived fields.** Every column is an untouched FPL API value. Compute xPts, form, or rolling averages downstream — the repo never bakes them in.
- **`fixture_code` is the sole join key.** Player history rows carry only `fixture_code`; all match context (opponent, venue, scores, kickoff) lives once in the fixtures CSV. This avoids duplicating mutable fixture data across thousands of player rows.
- **Stable column order.** Identity + join key lead each row; remaining stats follow in FPL API order so diffs stay clean across weekly scrapes.

---

## Update Cadence
| Dataset | Method | Frequency |
| :--- | :--- | :--- |
| **FPL data** | Automated — `.github/workflows/fpl_updater.yml` runs `scrape_teams.py` then `scrape_players.py`, commits the diff | Weekly (Tuesdays 12:00 UTC) + manual dispatch |
| **Historical PL archive** | Run locally, commit resulting CSVs | After each round |

The PulseLive endpoints powering `pl_stats/` are the Premier League's internal API. Running them from public CI risks rate-limiting and IP blocks, so that scrape stays local and only its CSV output is pushed.

---

## Getting Started

```bash
git clone https://github.com/imadeddine-belkat/Premier-League-Stats.git
cd Premier-League-Stats
pip install -r requirements.txt

# Run the FPL scrapers (writes into fpl_scraper/fpl_stats/)
cd fpl_scraper
python scrape_teams.py
python scrape_players.py
```

**Quick load in Pandas** (read the committed CSVs directly from GitHub):

```python
import pandas as pd

BASE = "https://raw.githubusercontent.com/imadeddine-belkat/Premier-League-Stats/main"

# All players, all gameweeks this season
players = pd.read_csv(f"{BASE}/fpl_scraper/fpl_stats/_index/players/2025-26_all_players_gw.csv")

top = (players.groupby(["first_name", "second_name"])["total_points"]
       .sum().sort_values(ascending=False).head(10))
print(top)
```

> Re-running the player scraper hits ~840 `element-summary` endpoints with a small politeness delay, so a full sync takes a few minutes.

---

## Use Cases

- **FPL managers** — backtest transfers and train expected-points (xPts) models on raw weekly data.
- **Football analysts** — study long-term tactical and event-level trends back to 2008 via the PulseLive archive.
- **Data viz / ML** — drop the `_index` and `_merged` CSVs straight into Pandas, R, Tableau, or Power BI.

---

## Data Caveats

- `pl_stats/` only includes seasons in which a given club actually competed in the Premier League.
- FPL underlying metrics (xG, xA, ICT) are the provider's own values and **may be revised post-match** — rows the API can still change are flagged via the `modified` column.
- **Lookahead bias:** any form/expected field the API updates after a deadline can leak future information. Shift such features by one gameweek or exclude them when training.
- The PulseLive `events_stats` schema can drift across seasons; merge tooling takes the column union, so older seasons may show empty cells for metrics introduced later.

---

## Contributing

Contributions, corrections, and historical backfills are welcome. Please open an issue describing the change before submitting a PR.

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

> **Disclaimer:** Unofficial dataset, not affiliated with or endorsed by the Premier League or Fantasy Premier League. Data is sourced from publicly accessible APIs for educational and analytical use.