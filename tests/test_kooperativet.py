import unittest
from unittest.mock import patch

import requests

from scrapers.kooperativet import KooperativetScraper


PAGE = """
<div id="monday" class="container_wrap">
  <h2>Lunch Måndag v.49</h2>
  <p><strong>KÖTT</strong><br> Köttbullar – Med mos</p>
</div>
<div id="after_section_4" class="container_wrap">
  <div class="flex_column">
    <h1> LUNCH FREDAG v49</h1>
    <p><strong>SALLADER</strong><br> Caesarsallad – Med kyckling</p>
    <p><strong>VECKANS SPECIAL</strong><br>Taco Bowl – Med ris</p>
    <p>Veg Taco Bowl – Med tofu</p>
    <p><strong>KÖTT</strong><br>Fredags Grillen – Gårdsgris<br>med pommes</p>
    <p><strong>FISK</strong><br>Havets Wallenbergare</p>
  </div>
  <div class="flex_column">
    <h1>–</h1>
    <p><strong>THAI</strong><br>Nasigoreng – Stekt ris</p>
    <p><strong>VEGETARISK</strong><br>Tofu - Med ris</p>
    <p><strong>INDISK</strong><br>Rogan Josh</p>
    <p><strong>VÄRLDEN</strong><br>Kebabpizza</p>
  </div>
</div>
<div class="container_wrap"><h3>Kontakt</h3><p>Ring oss</p></div>
"""


def response(html):
    result = requests.Response()
    result.status_code = 200
    result._content = html.encode("utf-8")
    result.encoding = "utf-8"
    return result


class KooperativetScraperTests(unittest.TestCase):
    @patch("scrapers.kooperativet.requests.get")
    def test_friday_without_weekday_id_includes_both_columns(self, get):
        get.return_value = response(PAGE)
        scraper = KooperativetScraper()
        menu = scraper.get_menu_for_day("FRIDAY")
        self.assertEqual(len(menu.items), 9)
        self.assertEqual([item.category for item in menu.items], [
            "SALLADER", "VECKANS SPECIAL", "VECKANS SPECIAL", "KÖTT", "FISK",
            "THAI", "VEGETARISK", "INDISK", "VÄRLDEN",
        ])
        self.assertEqual(menu.items[3].name, "Fredags Grillen")
        self.assertEqual(menu.items[3].description, "Gårdsgris med pommes")
        self.assertEqual(menu.items[-1].name, "Kebabpizza")
        self.assertIsNone(scraper.get_menu_for_day("saturday"))
        monday = scraper.get_menu_for_day("monday")
        self.assertEqual(len(monday.items), 1)
        self.assertEqual(monday.items[0].name, "Köttbullar")

    @patch("scrapers.kooperativet.requests.get")
    def test_existing_friday_id_still_works(self, get):
        get.return_value = response(PAGE.replace('id="after_section_4"', 'id="friday"'))
        scraper = KooperativetScraper()
        self.assertEqual(len(scraper.get_menu_for_day("friday").items), 9)

    @patch("scrapers.kooperativet.requests.get")
    def test_repeated_parsing_preserves_categories(self, get):
        get.return_value = response(PAGE)
        scraper = KooperativetScraper()
        before = [item.to_dict() for item in scraper.get_menu_for_day("friday").items]
        scraper.fetch()
        self.assertEqual(before, [item.to_dict() for item in scraper.get_menu_for_day("friday").items])

    @patch("scrapers.kooperativet.requests.get")
    def test_missing_heading_does_not_capture_other_content(self, get):
        get.return_value = response(PAGE.replace("LUNCH FREDAG", "Evenemang"))
        scraper = KooperativetScraper()
        self.assertIsNone(scraper.get_menu_for_day("friday"))
        self.assertEqual(list(scraper.get_all_menus()), ["monday"])


if __name__ == "__main__":
    unittest.main()
