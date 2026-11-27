import csv
import io
import unittest
from unittest.mock import patch

import requests

from scrapers.district_one import DistrictOneScraper


PAGE = """
<section id="lunch">
  <ul class="lunch-features-list"><li><strong>Pris:</strong> 135 kr.</li></ul>
  <button data-tab="lunch-mon">MÅNDAG</button>
  <div id="lunch-mon"><ul class="menu-list"></ul></div>
  <h3>Hela veckan</h3><ul id="lunch-all"></ul>
</section>
<section id="hotpot"><li>Hot pot 399 kr</li></section>
<script src="lunch.js"></script>
"""
SCRIPT = 'const SHEET_URL = "https://example.com/lunch.csv";'


def csv_menu():
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Dag", "Kategori", "Rätt (SV)", "Kategori (EN)", "Rätt (EN)"])
    writer.writerow(["Vecka 48", "", ""])
    for day in ["MÅNDAG", "Tisdag", "Onsdag", "Torsdag", "Fredag"]:
        writer.writerow([day, "Fisk", f'Torsk för {day}, med "sås"\noch potatis.', "Fish", "Cod"])
    writer.writerow([" Hela veckan ", " Poke bowl ", " Lax med ris, räkor och grönt. "])
    writer.writerow(["Hot pot", "Buljong", "Middagsbuffé"])
    writer.writerow(["Måndag", "Tom rätt", ""])
    writer.writerow([])
    writer.writerow(["Måndag"])
    return output.getvalue()


def response(text):
    result = requests.Response()
    result.status_code = 200
    result._content = text.encode("utf-8")
    return result


class DistrictOneScraperTests(unittest.TestCase):
    @patch("scrapers.district_one.requests.get")
    def test_weekdays_names_descriptions_and_all_week(self, get):
        get.side_effect = [response(PAGE), response(SCRIPT), response(csv_menu())]
        scraper = DistrictOneScraper()

        self.assertEqual(list(scraper.get_all_menus()), list(scraper.WEEKDAYS.values()))
        for day, menu in scraper.get_all_menus().items():
            self.assertEqual(menu.day, day)
            self.assertEqual([item.name for item in menu.items], ["Fisk", "Poke bowl"])
            self.assertEqual([item.price for item in menu.items], ["135 kr", "135 kr"])
            self.assertIsNone(menu.items[0].category)
            self.assertIn('med "sås"\noch potatis.', menu.items[0].description)
            self.assertEqual(menu.items[1].description, "Lax med ris, räkor och grönt.")
        self.assertIn("MÅNDAG", scraper.get_menu_for_day("MONDAY").items[0].description)
        self.assertIn("Fredag", scraper.get_menu_for_day("friday").items[0].description)
        self.assertIsNone(scraper.get_menu_for_day("saturday"))
        self.assertEqual(get.call_args_list[-1].args[0], "https://example.com/lunch.csv")
        self.assertTrue(all(call.kwargs["timeout"] == 30 for call in get.call_args_list))

    @patch("scrapers.district_one.requests.get")
    def test_fallback_for_failed_or_empty_spreadsheet(self, get):
        fallback = response('''{"days": {
          "mon": [{"cat": {"sv": "Fisk", "en": "Fish"}, "desc": {"sv": "Torsk"}}],
          "all": [{"cat": {"sv": "Poke bowl"}, "desc": {"sv": "Lax med ris"}}],
          "hotpot": [{"cat": {"sv": "Hot pot"}, "desc": {"sv": "Buffé"}}]
        }}''')
        for failure in [requests.Timeout(), response("Dag,Kategori,Rätt\nVecka 48,,"),
                        response("<html>Service unavailable</html>")]:
            with self.subTest(failure=failure):
                get.reset_mock()
                get.side_effect = [response(PAGE), response(SCRIPT), failure, fallback]
                scraper = DistrictOneScraper()
                self.assertEqual([item.name for item in scraper.get_menu_for_day("monday").items],
                                 ["Fisk", "Poke bowl"])
                self.assertEqual([item.name for item in scraper.get_menu_for_day("friday").items],
                                 ["Poke bowl"])
                self.assertEqual(get.call_args.args[0], "https://districtone.se/menu.json")

    @patch("scrapers.district_one.requests.get")
    def test_missing_price_does_not_use_hotpot_price(self, get):
        get.side_effect = [response(PAGE.replace("<strong>Pris:</strong> 135 kr.", "")),
                           response(SCRIPT), response(csv_menu())]
        scraper = DistrictOneScraper()
        self.assertIsNone(scraper.get_menu_for_day("monday").items[0].price)

    @patch("scrapers.district_one.requests.get")
    def test_refetch_clears_old_menus(self, get):
        get.side_effect = [response(PAGE), response(SCRIPT), response(csv_menu()),
                           response("<section id='hotpot'>Hot pot</section>")]
        scraper = DistrictOneScraper()
        scraper.fetch()
        self.assertEqual(scraper.get_all_menus(), {})

    @patch("scrapers.district_one.requests.get")
    def test_http_errors_are_reported(self, get):
        failed = response("Unavailable")
        failed.status_code = 503
        get.return_value = failed
        with self.assertRaises(requests.HTTPError):
            DistrictOneScraper()


if __name__ == "__main__":
    unittest.main()
