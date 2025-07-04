# scrapers/kooperativet.py

from bs4 import BeautifulSoup
import requests
from typing import Dict, Optional
from scrapers.base import LunchScraper, DailyMenu, MenuItem

class KooperativetScraper(LunchScraper):
    URL = "https://www.kooperativet.se/"
    _PRICE = "130 kr"

    def __init__(self):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(self.URL, headers=headers)
        response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "html.parser")
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    def fetch(self) -> None:
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            section = self.soup.find("div", {"id": day})
            if not section:
                continue

            paragraphs = section.find_all("p")
            current_category = None
            items = []

            for p in paragraphs:
                # Detect and extract <strong> category tags
                strong = p.find("strong")
                if strong:
                    current_category = strong.get_text(strip=True).strip(" :")
                    strong.extract()

                text = p.get_text(strip=True)
                if text:
                    # Try to split into name + description if a separator exists
                    if "-" in text:
                        name, desc = map(str.strip, text.split("-", 1))
                        items.append(MenuItem(name=name, description=desc, price=self._PRICE, category=current_category))
                    elif "–" in text:
                        name, desc = map(str.strip, text.split("–", 1))
                        items.append(MenuItem(name=name, description=desc, price=self._PRICE, category=current_category))
                    else:
                        items.append(MenuItem(name=text, price=self._PRICE, category=current_category))

            if items:
                self._menus[day] = DailyMenu(day=day, items=items)

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
