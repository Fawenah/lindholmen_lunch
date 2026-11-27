import json
import threading
import unittest
from contextlib import ExitStack
from unittest.mock import mock_open, patch

import main
from scrapers.base import DailyMenu, MenuItem


def menus():
    return {day: DailyMenu(day, [MenuItem("Lunch", description="Med potatis")])
            for day in main.WEEKDAYS}


class RunnerTests(unittest.TestCase):
    def runner(self, scrapers, existing=None):
        stack = ExitStack()
        self.addCleanup(stack.close)
        file = stack.enter_context(patch("main.open", mock_open(read_data=json.dumps(existing or {}))))
        stack.enter_context(patch("main.os.path.exists", return_value=True))
        stack.enter_context(patch("main.os.makedirs"))
        stack.enter_context(patch("main.SCRAPERS", scrapers))
        render = stack.enter_context(patch("main.generate_lunch_summary"))
        return file, render

    @staticmethod
    def written(file):
        return json.loads("".join(call.args[0] for call in file().write.call_args_list))

    def test_different_sites_overlap_and_duplicate_site_runs_once(self):
        # The first site cannot finish until the second starts. A sequential
        # runner fails this check without relying on elapsed-time thresholds.
        barrier = threading.Barrier(2, timeout=5)

        class First:
            calls = 0

            def __init__(self):
                type(self).calls += 1
                barrier.wait()

            def get_all_menus(self):
                return menus()

        class Second(First):
            calls = 0

        file, render = self.runner([First, Second, First])
        main.scrape_for_day("friday", refresh=True)
        self.assertEqual(set(self.written(file)), {"First", "Second"})
        self.assertEqual((First.calls, Second.calls), (1, 1))
        render.assert_called_once_with("friday")

    def test_weekly_instances_are_reused_across_days(self):
        class Weekly:
            calls = 0

            def __init__(self):
                type(self).calls += 1

            def get_all_menus(self):
                return menus()

        file, render = self.runner([Weekly])
        cache = {}
        for day in main.WEEKDAYS:
            file().write.reset_mock()
            main.scrape_for_day(day, refresh=True, cache=cache)
            self.assertEqual(self.written(file)["Weekly"]["day"], day)
        self.assertEqual(Weekly.calls, 1)
        self.assertEqual(render.call_count, 5)
        self.assertIsInstance(cache["Weekly"], Weekly)

    def test_retries_are_sequential_and_keep_failed_site_fallback(self):
        class Failed:
            calls = 0

            def __init__(self):
                type(self).calls += 1
                raise RuntimeError("Site unavailable")

        class Retried:
            calls = 0
            active = threading.Lock()

            def __init__(self):
                if not self.active.acquire(blocking=False):
                    raise AssertionError("Overlapping attempts for the same site")
                try:
                    type(self).calls += 1
                    if self.calls < 3:
                        raise RuntimeError("Temporary failure")
                finally:
                    self.active.release()

            def get_all_menus(self):
                return {}

            def get_menu_for_day(self, day):
                return DailyMenu(day, [MenuItem("Recovered lunch")])

        fallback = {"Failed": {"day": "friday", "items": [{"name": "Cached lunch"}]}}
        file, render = self.runner([Failed, Retried], fallback)
        with patch("main.time.sleep"), patch("main.traceback.print_exc"):
            main.scrape_for_day("friday", refresh=True)
        result = self.written(file)
        self.assertEqual(result["Failed"], fallback["Failed"])
        self.assertEqual(result["Retried"]["items"][0]["name"], "Recovered lunch")
        self.assertEqual((Failed.calls, Retried.calls), (3, 3))
        render.assert_called_once_with("friday")

    def test_cached_day_skips_scraping(self):
        file, render = self.runner([object])
        with patch("main._scrape_restaurant") as worker:
            main.scrape_for_day("friday")
        worker.assert_not_called()
        file().write.assert_not_called()
        render.assert_called_once_with("friday")


if __name__ == "__main__":
    unittest.main()
