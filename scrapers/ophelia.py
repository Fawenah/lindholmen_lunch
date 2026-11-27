import json
import re
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

from scrapers.base import DailyMenu, LunchScraper, MenuItem


class OpheliaScraper(LunchScraper):
    URL = "https://www.restaurangophelia.se/sv"
    WEEKDAYS = {1: "monday", 2: "tuesday", 3: "wednesday", 4: "thursday", 5: "friday"}

    def __init__(self):
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    @staticmethod
    def _lunch_week(soup):
        # Next.js embeds the complete week used by the weekday buttons. The
        # rendered HTML only contains the currently selected day's dishes.
        chunks = []
        for script in soup.find_all("script", src=False):
            match = re.fullmatch(r"\s*self\.__next_f\.push\((.*)\)\s*;?\s*", script.get_text(), re.S)
            if match:
                data = json.loads(match.group(1))
                if len(data) > 1 and data[0] == 1 and isinstance(data[1], str):
                    chunks.append(data[1])
        payload = "".join(chunks)
        # Scope extraction to the lunch section, avoiding other menu props.
        lunch = re.search(r'"id"\s*:\s*"lunch"', payload)
        if lunch:
            week = re.search(r'"week"\s*:\s*', payload[lunch.end():])
            if week:
                value, _ = json.JSONDecoder().raw_decode(payload[lunch.end() + week.end():])
                return value
        raise ValueError("Could not find Ophelia's weekly lunch data")

    def fetch(self) -> None:
        self._menus = {}
        response = requests.get(self.URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        week = self._lunch_week(soup)
        if not week:
            return  # No lunch week published.

        default_price = week.get("promoPriceSek")
        if default_price is None:
            default_price = week.get("priceSek")
        for number, day in self.WEEKDAYS.items():
            items = []
            dishes = [dish for dish in week.get("dishes", []) if dish.get("weekday") == number]
            for dish in sorted(dishes, key=lambda dish: dish.get("sortOrder", 0)):
                if not dish.get("name", "").strip():
                    continue
                price = dish.get("priceSek")
                if price is None:
                    price = default_price
                items.append(MenuItem(
                    name=dish["name"],
                    description=dish.get("description"),
                    price=f"{price:g} kr" if price is not None else None,
                ))
            if items:
                self._menus[day] = DailyMenu(day=day, items=items)

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
