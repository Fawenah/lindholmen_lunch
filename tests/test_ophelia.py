import json
import unittest
from unittest.mock import patch

import requests

from scrapers.ophelia import OpheliaScraper


FRIDAY = ["Viltgryta", "Panerad Spätta", "Sallad - Varmrökt Lax",
          "Sallad - Biff Yakuniki", "Sallad - Halloumi"]


def lunch_week():
    return {
        "priceSek": 139,
        "promoPriceSek": None,
        "alternativeDishes": [{"name": "Pizza Margherita"}],
        "dishes": [
            {"weekday": day, "name": name if day == 5 else f"{name} dag {day}",
             "description": 'Grönsaker, "sås" & potatis.',
             "priceSek": 149 if index > 1 else None, "sortOrder": index}
            for day in range(1, 6) for index, name in enumerate(FRIDAY)
        ],
    }


def page_response(week):
    # Include an unrelated menu before lunch and split the stream mid-object,
    # as Next.js can send data across multiple script elements.
    payload = '1:["$","section",null,{"id":"menu","week":{"dishes":[]}}]\n'
    payload += '2:' + json.dumps(["$", "section", None, {
        "id": "lunch", "children": ["$", "$L1", None, {"week": week}],
    }], ensure_ascii=False)
    split = len(payload) // 2
    scripts = "".join(
        f'<script>self.__next_f.push({json.dumps([1, part])})</script>'
        for part in [payload[:split], payload[split:]]
    )
    response = requests.Response()
    response.status_code = 200
    response._content = ('<meta charset="utf-8"><section id="menu"><h3>Steak</h3></section>'
                         '<section id="lunch"><h3>Viltgryta</h3></section>' + scripts).encode("utf-8")
    return response


class OpheliaScraperTests(unittest.TestCase):
    @patch("scrapers.ophelia.requests.get")
    def test_all_weekdays_and_friday_dishes(self, get):
        week = lunch_week()
        week["dishes"].reverse()  # Display order comes from sortOrder.
        get.return_value = page_response(week)
        scraper = OpheliaScraper()
        self.assertEqual(list(scraper.get_all_menus()), list(scraper.WEEKDAYS.values()))
        for menu in scraper.get_all_menus().values():
            self.assertEqual(len(menu.items), 5)
            self.assertEqual([item.price for item in menu.items],
                             ["139 kr", "139 kr", "149 kr", "149 kr", "149 kr"])
        friday = scraper.get_menu_for_day("FRIDAY")
        self.assertEqual([item.name for item in friday.items], FRIDAY)
        self.assertEqual(friday.items[0].description, 'Grönsaker, "sås" & potatis.')
        self.assertIsNone(scraper.get_menu_for_day("saturday"))
        get.assert_called_once_with(OpheliaScraper.URL, timeout=30)

    @patch("scrapers.ophelia.requests.get")
    def test_promo_price_and_missing_description(self, get):
        week = lunch_week()
        week["promoPriceSek"] = 129
        week["dishes"][20]["description"] = None
        get.return_value = page_response(week)
        scraper = OpheliaScraper()
        friday = scraper.get_menu_for_day("friday")
        self.assertEqual(friday.items[0].price, "129 kr")
        self.assertIsNone(friday.items[0].description)
        self.assertEqual(friday.items[2].price, "149 kr")

    @patch("scrapers.ophelia.requests.get")
    def test_no_published_week_clears_menus(self, get):
        get.side_effect = [page_response(lunch_week()), page_response(None)]
        scraper = OpheliaScraper()
        scraper.fetch()
        self.assertEqual(scraper.get_all_menus(), {})

    @patch("scrapers.ophelia.requests.get")
    def test_missing_data_raises_instead_of_using_fixed_menu(self, get):
        get.return_value = page_response(lunch_week())
        get.return_value._content = b'<section id="menu"><h3>Steak</h3></section>'
        with self.assertRaises(ValueError):
            OpheliaScraper()

    @patch("scrapers.ophelia.requests.get")
    def test_http_error(self, get):
        get.return_value = page_response(None)
        get.return_value.status_code = 503
        with self.assertRaises(requests.HTTPError):
            OpheliaScraper()


if __name__ == "__main__":
    unittest.main()
