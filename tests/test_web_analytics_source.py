import unittest

from app.services.analytics_service import _traffic_source


class WebAnalyticsSourceTests(unittest.TestCase):
    def test_root_landing_without_referrer_is_direct(self):
        source = _traffic_source(
            referrer=None,
            origin="https://quizz-fe-cntt.vercel.app",
            path="/",
        )

        self.assertEqual(source, "direct")

    def test_root_landing_same_origin_referrer_is_direct(self):
        source = _traffic_source(
            referrer="https://quizz-fe-cntt.vercel.app/",
            origin="https://quizz-fe-cntt.vercel.app",
            path="/",
        )

        self.assertEqual(source, "direct")

    def test_non_root_same_origin_referrer_is_internal(self):
        source = _traffic_source(
            referrer="https://quizz-fe-cntt.vercel.app/",
            origin="https://quizz-fe-cntt.vercel.app",
            path="/student",
        )

        self.assertEqual(source, "internal")

    def test_external_search_to_root_still_counts_as_search(self):
        source = _traffic_source(
            referrer="https://www.google.com/search?q=quizzvn",
            origin="https://quizz-fe-cntt.vercel.app",
            path="/",
        )

        self.assertEqual(source, "search")


if __name__ == "__main__":
    unittest.main()