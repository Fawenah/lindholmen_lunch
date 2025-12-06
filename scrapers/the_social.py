# file: scrapers/gansu.py

import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from scrapers.base import LunchScraper, DailyMenu, MenuItem

class TheSocialScraper(LunchScraper):
    URL = "https://www.strawberryhotels.com/restaurant/sweden/gothenburg/the-social-eriksberg/"
    JSON_PATH = Path("scrapers/the_social.json")

    def __init__(self):
        with open(self.JSON_PATH, encoding="utf-8") as f:
            self.menu_data = json.load(f)
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    def fetch(self) -> None:
        """
        The Social has a fixed menu that is the same every weekday.
        We build one list of MenuItem objects and reuse it for Mon–Fri.
        """
        # Build category-specific lists from the JSON
        snacks = [
            MenuItem(**item, category="Snacks")
            for item in self.menu_data.get("snacks", [])
        ]

        appetizers = [
            MenuItem(**item, category="Förrätter")
            for item in self.menu_data.get("appetizers", [])
        ]

        desserts = [
            MenuItem(**item, category="Efterrätter")
            for item in self.menu_data.get("desserts", [])
        ]

        deals = [
            MenuItem(**item, category="Erbjudanden")
            for item in self.menu_data.get("deals", [])
        ]

        main_courses = [
            MenuItem(**item, category="Varmrätter")
            for item in self.menu_data.get("main_courses", [])
        ]

        sides = [
            MenuItem(**item, category="Sides")
            for item in self.menu_data.get("sides", [])
        ]

        # One fixed list for all weekdays
        all_items = []
        # Add that lunch menu is coming soon
        all_items.append(MenuItem(name="Lunchmeny kommer snart", description="", price=""))
        all_items.extend(snacks)
        all_items.extend(appetizers)
        all_items.extend(desserts)
        all_items.extend(deals)
        all_items.extend(main_courses)
        all_items.extend(sides)

        # Same menu Monday–Friday
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            # Use a copy of the list so accidental mutations per day don't leak
            self._menus[day] = DailyMenu(day=day, items=list(all_items))

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
