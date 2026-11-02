import unittest

from housing_regression.steam_review_multiplier import (
    engineer_row,
    parse_list,
    parse_owners,
    review_count,
)


class SteamParsingTests(unittest.TestCase):
    def test_owner_interval_is_not_collapsed(self):
        self.assertEqual(parse_owners("1,000 - 2,000"), (1000.0, 2000.0))
        self.assertIsNone(parse_owners("unknown"))
        self.assertIsNone(parse_owners("200 - 100"))

    def test_review_count_prefers_total_and_falls_back_only_when_missing(self):
        self.assertEqual(review_count({"num_reviews_total": "31", "positive": "20", "negative": "10"}), (31.0, "num_reviews_total"))
        self.assertEqual(review_count({"num_reviews_total": "", "positive": "20", "negative": "10"}), (30.0, "positive_plus_negative"))

    def test_list_parser_supports_list_dict_and_missing(self):
        self.assertEqual(parse_list("['Action', 'RPG']"), ["Action", "RPG"])
        self.assertEqual(parse_list("{'FPS': 20, 'RPG': 4}"), ["FPS", "RPG"])
        self.assertEqual(parse_list("[]"), [])

    def test_engineering_maps_realistic_fields(self):
        features = engineer_row({
            "genres": "['Action', 'RPG']", "categories": "['Single-player']",
            "tags": "{'Souls-like': 4}", "price": "19.99", "required_age": "0",
            "dlc_count": "2", "achievements": "20", "release_date": "2021-08-09",
            "windows": "true", "mac": "false", "linux": "true",
            "supported_languages": "['English', 'Traditional Chinese']",
            "full_audio_languages": "['English']", "discount": "15",
            "developers": "['Studio A']", "publishers": "['Publisher A']",
            "screenshots": "['shot-1', 'shot-2']", "movies": "['trailer']",
            "website": "https://example.invalid",
        })
        self.assertEqual(features["release_year"], 2021.0)
        self.assertEqual(features["genre_count"], 2.0)
        self.assertEqual(features["has_traditional_chinese"], 1.0)
        self.assertEqual(features["tag_count"], 1.0)
        self.assertEqual(features["developer_count"], 1.0)
        self.assertEqual(features["publisher_count"], 1.0)
        self.assertEqual(features["screenshot_count"], 2.0)
        self.assertEqual(features["movie_count"], 1.0)
        self.assertEqual(features["has_website"], 1.0)
        missing = engineer_row({"genres": "", "categories": "[]", "tags": "", "supported_languages": ""})
        self.assertTrue(__import__("math").isnan(missing["genre_count"]))
        self.assertEqual(missing["category_count"], 0.0)
        self.assertTrue(__import__("math").isnan(missing["supported_language_count"]))
        self.assertTrue(__import__("math").isnan(missing["developer_count"]))
        self.assertEqual(missing["has_website"], 0.0)
        explicit_empty = engineer_row({"developers": "[]", "publishers": "[]", "screenshots": "[]", "movies": "[]"})
        for field in ("developer_count", "publisher_count", "screenshot_count", "movie_count"):
            self.assertEqual(explicit_empty[field], 0.0)


if __name__ == "__main__":
    unittest.main()
