# A collection of item ids & weights, used to record consumption and production of a method, weights should represent the amount produced per period
from Scripts.python3.lib.pip._vendor import requests

import item_ids
import numpy as np


class ItemIndex:
    def __init__(self, *items):
        self.items = items


BASE_URL = "https://prices.runescape.wiki/api/v2/osrs"
session = requests.Session()
session.headers["User-Agent"] = (
    "milp"
)


def fetch(endpoint, **params):
    response = session.get(
        f"{BASE_URL}/{endpoint}",
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_timeseries(item_id: int, timestep: str = "30d") -> dict:
    return fetch("timeseries", id=item_id, lookback=timestep)


class LivePrices:
    def __init__(self):
        self.cache = {
            int(item_id): data for item_id, data in fetch("24h")["data"].items()
        }

    def lookup(self, id):
        if id == 995:  # coins
            return {
                "invalid": True,
                "avgHighPrice": 1,
                "highPriceVolume": 1,
                "avgLowPrice": 1_000_000_000,
                "lowPriceVolume": 1_000_000_000,
            }

        if id not in self.cache:
            return {
                "invalid": True,
                "avgHighPrice": 0,
                "highPriceVolume": 0,
                "avgLowPrice": 0,
                "lowPriceVolume": 0,
            }

        return self.cache[id]