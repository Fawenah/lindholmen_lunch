# file: scrapers/gansu.py

import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from scrapers.base import LunchScraper, DailyMenu, MenuItem

class GansuScraper(LunchScraper):
    URL = "https://www.google.com/maps/place/Gansu+K%C3%B6ket/@57.7115577,11.936209,1494m/data=!3m1!1e3!4m6!3m5!1s0x464ff326ee84308b:0x530f50bd2a58cbb!8m2!3d57.7116798!4d11.9451144!16s%2Fg%2F11tc8r235n?entry=ttu&g_ep=EgoyMDI1MTIwMi4wIKXMDSoASAFQAw%3D%3D"
    JSON_PATH = Path("scrapers/gansu_lunch_all_weeks.json")

    def __init__(self):
        with open(self.JSON_PATH, encoding="utf-8") as f:
            self.menu_data = json.load(f)
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    def fetch(self) -> None:
        """
        Gansu has a fixed menu that is the same every weekday.
        We build one list of MenuItem objects and reuse it for Mon–Fri.
        """
        # Build category-specific lists from the JSON
        sour_soup = [
            MenuItem(**item, category="Dumplings med surstark biffsoppa")
            for item in self.menu_data.get("soursoup", [])
        ]

        beefnoodle_soup = [
            MenuItem(**item, category="Biffnudelsoppor")
            for item in self.menu_data.get("beefnoodlesoup", [])
        ]

        zhajiang = [
            MenuItem(**item, category="Zhajiang nudlar")
            for item in self.menu_data.get("zhajiang", [])
        ]

        xiaolongbao = [
            MenuItem(**item, category="Xiaolong Bao")
            for item in self.menu_data.get("xiaolongbao", [])
        ]

        sides_items = [
            MenuItem(**item, category="Övrigt")
            for item in self.menu_data.get("misc", [])
        ]

        # One fixed list for all weekdays
        all_items = []
        all_items.extend(sour_soup)
        all_items.extend(beefnoodle_soup)
        all_items.extend(zhajiang)
        all_items.extend(xiaolongbao)
        all_items.extend(sides_items)

        # Same menu Monday–Friday
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            # Use a copy of the list so accidental mutations per day don't leak
            self._menus[day] = DailyMenu(day=day, items=list(all_items))

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
