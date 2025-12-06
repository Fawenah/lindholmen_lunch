# file: scrapers/gansu.py

import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from scrapers.base import LunchScraper, DailyMenu, MenuItem

class AlkemistenScraper(LunchScraper):
    URL = "https://www.alkemistenkaffebar.se/"
    JSON_PATH = Path("scrapers/alkemisten.json")

    def __init__(self):
        with open(self.JSON_PATH, encoding="utf-8") as f:
            self.menu_data = json.load(f)
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    def fetch(self) -> None:
        """
        Alkemisten has a fixed menu that is the same every weekday.
        We build one list of MenuItem objects and reuse it for Mon–Fri.
        """
        # Build category-specific lists from the JSON
        vegetarian = [
            MenuItem(**item, category="Vegetariskt")
            for item in self.menu_data.get("vegetarian", [])
        ]

        vegan = [
            MenuItem(**item, category="Veganskt")
            for item in self.menu_data.get("vegan", [])
        ]

        # One fixed list for all weekdays
        all_items = []
        all_items.extend(vegetarian)
        all_items.extend(vegan)

        # Same menu Monday–Friday
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            # Use a copy of the list so accidental mutations per day don't leak
            self._menus[day] = DailyMenu(day=day, items=list(all_items))

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
