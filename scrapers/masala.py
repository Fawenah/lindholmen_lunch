# file: scrapers/masala.py

import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from scrapers.base import LunchScraper, DailyMenu, MenuItem

class MasalaScraper(LunchScraper):
    URL = "https://masalakitchen.se/lunch/"
    JSON_PATH = Path("scrapers/masala_lunch_all_weeks.json")

    def __init__(self):
        with open(self.JSON_PATH, encoding="utf-8") as f:
            self.menu_data = json.load(f)
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    def fetch(self) -> None:
        current_week = datetime.today().isocalendar().week
        week_key = f"week{((current_week - 1) % 4) + 1}"
        daily_menus = self.menu_data["weeks"].get(week_key, {})
        standing_items = [MenuItem(**item, category="Stående meny") for item in self.menu_data.get("standing", [])]
        sides_items = [MenuItem(**item, category="Tillbehör") for item in self.menu_data.get("sides", [])]

        for day, dishes in daily_menus.items():
            # Add an heading with a warning that the daily menu is out of date
            items = [MenuItem(name="Varning: Dagens meny kan vara inaktuell", category="Varning")]
            items.extend([MenuItem(**dish) for dish in dishes])
            items.extend(standing_items)
            items.extend(sides_items)
            self._menus[day.lower()] = DailyMenu(day=day.lower(), items=items)

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
