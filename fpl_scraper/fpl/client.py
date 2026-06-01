"""Typed-ish wrapper over the FPL endpoints, with disk caching for the
per-player element-summary calls (the only expensive, high-volume endpoint).
"""
import json
import logging
import time
from pathlib import Path

import requests

from . import config
from .http import get_json

log = logging.getLogger("fpl")


class FPLClient:
    def __init__(self, session: requests.Session, season: str,
                 cache_dir: Path = config.CACHE_DIR):
        self.session = session
        self.season = season
        self.cache_dir = cache_dir / season

    def bootstrap(self) -> dict:
        return get_json(self.session, config.BASE_URL + "bootstrap-static/")

    def current_season(self, boot: dict | None = None) -> str:
        return config.season_from_bootstrap(boot or self.bootstrap())

    def fixtures(self) -> list[dict]:
        return get_json(self.session, config.BASE_URL + "fixtures/")

    def fixture_codes(self) -> dict[int, int]:
        return {f["id"]: f["code"] for f in self.fixtures()}

    def player_summary(self, player_id: int) -> dict | None:
        cache_path = self.cache_dir / f"player_{player_id}.json"
        if cache_path.exists():
            with cache_path.open(encoding="utf-8") as f:
                return json.load(f)

        url = f"{config.BASE_URL}element-summary/{player_id}/"
        try:
            payload = get_json(self.session, url)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f)
        time.sleep(config.PLAYER_FETCH_DELAY) 
        return payload