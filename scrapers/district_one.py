import csv
import io
import logging
import re
from typing import Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrapers.base import DailyMenu, LunchScraper, MenuItem

logger = logging.getLogger(__name__)


class DistrictOneScraper(LunchScraper):
    URL = "https://districtone.se/"
    WEEKDAYS = {
        "mon": "monday", "tue": "tuesday", "wed": "wednesday",
        "thu": "thursday", "fri": "friday",
    }
    SHEET_DAYS = {
        "måndag": "mon", "tisdag": "tue", "onsdag": "wed",
        "torsdag": "thu", "fredag": "fri", "hela veckan": "all",
    }

    def __init__(self):
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    @staticmethod
    def _get(url):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        # Both the site and its spreadsheet use UTF-8.
        response.encoding = "utf-8-sig"
        return response

    def _load_days(self, soup):
        # Lunch lists in the HTML are empty: lunch.js populates them from CSV.
        # Discover the URL so a replacement spreadsheet is picked up too.
        try:
            script = soup.find("script", src=re.compile(r"(?:^|/)lunch\.js(?:\?|$)"))
            if script is None:
                raise ValueError("Lunch script not found")
            javascript = self._get(urljoin(self.URL, script["src"])).text
            sheet = re.search(r'''\bSHEET_URL\s*=\s*["']([^"']+)["']''', javascript)
            if sheet is None:
                raise ValueError("Lunch spreadsheet URL not found")
            rows = csv.reader(io.StringIO(self._get(sheet.group(1)).text))
            next(rows, None)  # Column headings, followed by week and dish rows.
            days = {key: [] for key in (*self.WEEKDAYS, "all")}
            for row in rows:
                if len(row) < 3:
                    continue
                day = self.SHEET_DAYS.get(row[0].strip().lower())
                if day and row[2].strip():
                    days[day].append({
                        "cat": {"sv": row[1].strip()},
                        "desc": {"sv": row[2].strip()},
                    })
            if not any(days.values()):
                raise ValueError("Lunch spreadsheet contains no dishes")
            return days
        except (requests.RequestException, ValueError) as exc:
            # Match the website's fallback when the live sheet is unavailable.
            logger.warning("Could not load District One lunch spreadsheet: %s", exc)
            return self._get(urljoin(self.URL, "menu.json")).json()["days"]

    def fetch(self):
        self._menus = {}
        soup = BeautifulSoup(self._get(self.URL).text, "html.parser")
        lunch = soup.find(id="lunch")
        if lunch is None:
            logger.warning("Could not find District One lunch section")
            return

        price = None
        for feature in lunch.select(".lunch-features-list li"):
            text = feature.get_text(" ", strip=True)
            if re.match(r"Pris\s*:", text, re.I):
                match = re.search(r"\d+(?:[.,]\d+)?\s*kr", text)
                if match:
                    price = match.group(0)

        days = self._load_days(soup)
        for key, day in self.WEEKDAYS.items():
            items = []
            for dish in days.get(key, []) + days.get("all", []):
                description = dish.get("desc", {}).get("sv", "").strip()
                if description:
                    # "cat" is the right-hand dish label; "desc" is on the left.
                    items.append(MenuItem(
                        name=dish.get("cat", {}).get("sv", ""),
                        description=description,
                        price=price,
                    ))
            if items:
                self._menus[day] = DailyMenu(day=day, items=items)

    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
