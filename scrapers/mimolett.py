# file: scrapers/mimolett.py

from bs4 import BeautifulSoup, NavigableString, Tag
from scrapers.base import LunchScraper, MenuItem, DailyMenu
from typing import Dict, List, Optional
import requests


class MimolettScraper(LunchScraper):
    PRIMARY_URL = "https://restaurangmimolett.se/lunch/"
    BACKUP_URL = "https://www.kvartersmenyn.se/index.php/rest/13278/"
    _PRICE = "129 kr"

    def __init__(self):
        self._menus: Dict[str, DailyMenu] = {}
        self.fetch()

    # -----------------------
    # Public fetch entrypoint
    # -----------------------
    def fetch(self) -> None:
        items: List[MenuItem] = []

        # 1) Try primary page
        try:
            response = requests.get(self.PRIMARY_URL, timeout=10)
            response.raise_for_status()
            items = self._parse_primary(response.text)
        except Exception as e:
            print(f"[Mimolett] Failed to fetch or parse primary page: {e}")

        # 2) Fallback to kvartersmenyn if primary failed or returned nothing
        if not items:
            try:
                backup_response = requests.get(self.BACKUP_URL, timeout=10)
                backup_response.raise_for_status()
                items = self._parse_backup(backup_response.text)
            except Exception as e:
                print(f"[Mimolett] Failed to fetch or parse backup page: {e}")
                items = []

        # If still no items, leave _menus empty so the caller can keep old JSON
        if not items:
            return

        # Mimolett serves same menu Mon–Fri
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            # Use a copy so later accidental mutation per day doesn't affect all
            self._menus[day] = DailyMenu(day=day, items=list(items))

    # -----------------------
    # Primary site parser
    # -----------------------
    def _parse_primary(self, html: str) -> List[MenuItem]:
        """
        Parse https://restaurangmimolett.se/lunch/
        (existing structure with .menu-list blocks).
        """
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select("div.menu-list")

        items: List[MenuItem] = []

        for container in containers:
            category_elem = container.select_one("h2.menu-list__title")
            if not category_elem:
                continue
            category = category_elem.get_text(strip=True)

            for li in container.select("li.menu-list__item"):
                name_el = li.select_one(".item_title")
                desc_el = li.select_one(".desc__content")
                price_el = li.select_one(".menu-list__item-price")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                description = desc_el.get_text(strip=True) if desc_el else None

                if price_el:
                    raw_price = price_el.get_text(strip=True)
                    # Normalize "129:-" -> "129 kr"
                    price = raw_price.replace(":-", " kr")
                else:
                    price = self._PRICE

                items.append(
                    MenuItem(
                        name=name,
                        description=description,
                        category=category,
                        price=price,
                    )
                )

        return items


    def _clean_description(self, desc: str) -> str:
        """
        Clean up descriptions from kvartersmenyn:

        - Strip low-opacity marker codes (pogre, bii, bei, cbf, ca)
        - Cut everything after 'SMAKLIG MÅLTID!' (incl. emojis)
        - Normalize whitespace and trailing commas/spaces
        """
        import re

        if not desc:
            return ""

        # Cut off footer + emojis
        parts = re.split(r"SMAKLIG MÅLTID!\s*", desc, flags=re.IGNORECASE)
        desc = parts[0]

        # Remove marker codes (the faint little "pogre", "bii", "bei", "cbf", "ca")
        desc = re.sub(r"\b(pogre|bii|bei|cbf|ca)\b", "", desc, flags=re.IGNORECASE)

        # Collapse multiple spaces
        desc = re.sub(r"\s{2,}", " ", desc)

        return desc.strip(" ,")


    # -----------------------
    # Backup (kvartersmenyn) parser
    # -----------------------
    def _parse_backup(self, html: str) -> List[MenuItem]:
        """
        Parse https://www.kvartersmenyn.se/index.php/rest/13278/

        The lunch menu is inside <div class="meny"> blocks.

        We parse in two steps:
        1) Collect all bold/strong texts to know which lines are categories and dish names.
        2) Flatten the menu to plain text lines (using <br> as line breaks), then walk
           line-by-line:
           - Category headers: KÖTT & FISK, RISOTTO, PASTARÄTTER
           - Dish name = any bold text that isn't a category
           - Description = following line(s) until the next category/dish/footer.
        """
        soup = BeautifulSoup(html, "html.parser")
        meny_divs = soup.select("div.meny")

        items: List[MenuItem] = []

        CATEGORY_NAMES = {"KÖTT & FISK", "RISOTTO", "PASTARÄTTER"}
        MARKER_CODES = {"pogre", "bii", "bei", "cbf", "ca"}

        for meny in meny_divs:
            # Skip the second block with PRIS information
            full_text_upper = meny.get_text(" ", strip=True).upper()
            if "PRIS:" in full_text_upper:
                continue

            # 1) Collect bold/strong texts for this meny
            bold_tags = meny.find_all(["b", "strong"])
            bold_texts = [b.get_text(" ", strip=True) for b in bold_tags]
            bold_set = set(bold_texts)

            # 2) Flatten to plain text lines (using <br> as explicit newlines)
            inner_html = "".join(str(child) for child in meny.children)
            inner_html = inner_html.replace("<br/>", "<br>").replace("<br>", "<br>\n")
            s2 = BeautifulSoup(inner_html, "html.parser")
            text_block = s2.get_text("\n")

            # Strip empty lines
            lines = [line.strip() for line in text_block.split("\n") if line.strip()]

            current_category: Optional[str] = None
            i = 0

            while i < len(lines):
                line = lines[i]

                # Safety: stop if we hit a PRIS-line (shouldn't happen here, but cheap)
                if "PRIS:" in line.upper():
                    break

                # Category header?
                if line.upper() in CATEGORY_NAMES:
                    current_category = line
                    i += 1
                    continue

                # Dish name? (bold text that isn't a category)
                if line in bold_set and line.upper() not in CATEGORY_NAMES:
                    name = line
                    desc_parts: List[str] = []

                    j = i + 1
                    while j < len(lines):
                        nxt = lines[j]

                        # Stop when we hit next category, next dish, or footer
                        if (
                            nxt.upper() in CATEGORY_NAMES
                            or (nxt in bold_set)
                            or nxt.upper() == "SMAKLIG MÅLTID!"
                        ):
                            break

                        # Skip marker-code-only lines
                        if nxt.lower() in MARKER_CODES:
                            j += 1
                            continue

                        desc_parts.append(nxt)
                        j += 1

                    raw_desc = " ".join(desc_parts).strip()
                    description = self._clean_description(raw_desc)

                    items.append(
                        MenuItem(
                            name=name,
                            description=description or None,
                            category=current_category or "Lunchmeny",
                            price=self._PRICE,
                        )
                    )

                    # Continue scanning from after the description we just consumed
                    i = j
                    continue

                # Any other line (free text, we just skip)
                i += 1

        return items



    # -----------------------
    # Public API
    # -----------------------
    def get_menu_for_day(self, day: str) -> Optional[DailyMenu]:
        return self._menus.get(day.lower())

    def get_all_menus(self) -> Dict[str, DailyMenu]:
        return self._menus
