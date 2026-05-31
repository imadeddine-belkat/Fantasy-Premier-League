"""HTTP layer: a single retrying session used by all callers.

Your players script had retries in two places — a urllib3 `Retry` adapter AND a
hand-rolled `get_with_retry` loop. The adapter already covers transient network
errors and the listed status codes, so the manual loop was redundant. This is
the one source of truth.
"""
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("fpl")


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        # raise on the final failed attempt instead of returning the bad response
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    return s


def get_json(session: requests.Session, url: str) -> dict | list:
    """GET + parse JSON. Raises for non-2xx so callers fail loudly, not silently."""
    res = session.get(url, timeout=(10, 30))
    res.raise_for_status()
    return res.json()