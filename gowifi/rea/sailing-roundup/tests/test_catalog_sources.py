#!/usr/bin/env python3
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from catalog_sources import classify_locality, source_links_from_config
from entity_match import DEFAULT_SPONSORS, build_index, match_text
from event_social_verify import class_config_links, verify_post
from facebook_cross_share import match_cross_shares, parse_shared_post, resolve_facebook_url
from social_collect import club_config, known_club_posts


class Locality(unittest.TestCase):
    def test_420_rsa_group_is_local(self):
        self.assertEqual(
            classify_locality("https://www.facebook.com/groups/120115671476306/", "420 Class RSA"),
            "local",
        )
        self.assertEqual(
            classify_locality("https://www.facebook.com/share/g/1Jh51CDMew/", "420 Class RSA"),
            "local",
        )
        self.assertEqual(
            classify_locality("https://www.facebook.com/420nationalssouthafrica/"),
            "local",
        )

    def test_international_marked_not_local(self):
        self.assertEqual(classify_locality("https://www.facebook.com/Int420Class/"), "not_local")
        self.assertEqual(classify_locality("https://int505.org/"), "not_local")
        self.assertEqual(classify_locality("https://dart18class.com/"), "not_local")
        self.assertEqual(classify_locality("https://linktr.ee/int420class"), "not_local")

    def test_sa_class_sites_are_local(self):
        self.assertEqual(classify_locality("https://www.revolutionise.com.au/dabchickca/"), "local")
        self.assertEqual(classify_locality("https://www.hobiesa.co.za/"), "local")
        self.assertEqual(classify_locality("https://rsa505.org.za/"), "local")


class EntityMatch(unittest.TestCase):
    def setUp(self):
        self.index = build_index(
            clubs=[{"code": "TSC", "name": "Theewater Sports Club", "slug": "tsc"}],
            classes=[{"name": "420", "slug": "420"}, {"name": "Dabchick", "slug": "dabchick"}],
            sailors=[{"name": "Joshua Keytel", "sa_id": "13522", "slug": "joshua-keytel-13522"}],
            sponsors=DEFAULT_SPONSORS,
        )

    def test_class_rsa_group_maps_to_class_page(self):
        hit = match_text("420 Class RSA", self.index)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["entity_type"], "class")
        self.assertEqual(hit["sailingsa_url"], "https://sailingsa.co.za/class/420")

    def test_club_page_maps_to_club_url(self):
        hit = match_text("Theewater Sports Club", self.index)
        self.assertEqual(hit["entity_type"], "club")
        self.assertEqual(hit["sailingsa_url"], "https://sailingsa.co.za/club/tsc")

    def test_sailor_and_sponsor(self):
        sailor = match_text("Joshua Keytel", self.index)
        self.assertEqual(sailor["entity_type"], "sailor")
        self.assertIn("/sailor/", sailor["sailingsa_url"])
        sponsor = match_text("North Sails", self.index)
        self.assertEqual(sponsor["entity_type"], "sponsor")


class CrossShare(unittest.TestCase):
    def test_parse_shared_caption(self):
        parsed = parse_shared_post("Theewater Sports Club shared 420 Class RSA's post")
        self.assertEqual(parsed["shared_by"], "Theewater Sports Club")
        self.assertEqual(parsed["shared_from"], "420 Class RSA")

    def test_cross_share_matches_sailingsa_urls(self):
        index = build_index(
            clubs=[{"code": "TSC", "name": "Theewater Sports Club", "slug": "tsc"}],
            classes=[{"name": "420", "slug": "420"}],
        )
        hits = match_cross_shares(
            [
                {
                    "url": "https://www.facebook.com/theewatersportsclub/posts/1",
                    "title": "Theewater Sports Club shared 420 Class RSA's post",
                    "description": "Nationals photos",
                }
            ],
            index,
        )
        self.assertTrue(hits)
        self.assertEqual(hits[0]["shared_from_entity"]["sailingsa_url"], "https://sailingsa.co.za/class/420")
        self.assertEqual(hits[0]["shared_by_entity"]["sailingsa_url"], "https://sailingsa.co.za/club/tsc")

    def test_resolve_420_share_group(self):
        resolved = resolve_facebook_url("https://www.facebook.com/share/g/1Jh51CDMew/?mibextid=wwXIfr")
        self.assertEqual(resolved["canonical_url"], "https://www.facebook.com/groups/120115671476306/")
        self.assertEqual(resolved["kind"], "facebook_group")
        if resolved.get("title"):
            self.assertIn("420", resolved["title"])


class ClassConfig(unittest.TestCase):
    def test_local_420_group_listed(self):
        links = class_config_links(["420"])
        urls = [x["url"] for x in links]
        self.assertIn("https://www.facebook.com/groups/120115671476306/", urls)
        local = [x for x in links if x.get("locality") == "local"]
        not_local = [x for x in links if x.get("locality") == "not_local"]
        self.assertTrue(local)
        self.assertTrue(not_local)
        only_local = class_config_links(["420"], local_only=True)
        self.assertTrue(all(x.get("locality") != "not_local" for x in only_local))

    def test_legacy_keys_still_read(self):
        cfg = {"facebook": "https://www.facebook.com/420nationalssouthafrica/", "website": "https://example.co.za"}
        links = source_links_from_config(cfg, "t")
        self.assertEqual(len(links), 2)


class HostClubDart(unittest.TestCase):
    def test_hmyc_seeded_dart_share(self):
        cfg = club_config("HMYC")
        self.assertEqual(cfg.get("facebook"), "https://www.facebook.com/henleymidmaryachtclub")
        posts = known_club_posts("HMYC", {"title": "Dart 18 Nationals", "id": "2026-09-24-hmyc-dart-18-nationals"})
        urls = " ".join(p.get("share_url") or p.get("url") or "" for p in posts)
        self.assertIn("1PGpY1pGh1", urls)

    def test_hmyc_dart_results_post_verifies(self):
        event = {
            "id": "2026-09-24-hmyc-dart-18-nationals",
            "title": "Dart 18 Nationals incorporating the KZN provincials",
            "club": "HMYC",
            "club_name": "Henley Midmar Yacht Club",
            "class_slugs": ["dart-18"],
            "host_club_facebook": "https://www.facebook.com/henleymidmaryachtclub",
            "event_url": "https://sailingsa.co.za/regatta/2026-09-24-hmyc-dart-18-nationals",
        }
        post = {
            "url": "https://www.facebook.com/henleymidmaryachtclub/posts/-dart-18-nationals-final-results-what-a-day-on-the-water-congratulations-to-all-/1633819895206118",
            "title": "HMYC - Henley Midmar Yacht Club",
            "description": "DART 18 NATIONALS – Final results! What a day on the water!",
        }
        check = verify_post(post, event)
        self.assertTrue(check["verified"], check)
        self.assertIn("host_club_page", check["reasons"])

    def test_resolve_hmyc_dart_share(self):
        resolved = resolve_facebook_url("https://www.facebook.com/share/p/1PGpY1pGh1/?mibextid=wwXIfr")
        self.assertIn("henleymidmaryachtclub", (resolved.get("canonical_url") or "").lower())
        self.assertIn("dart", (resolved.get("canonical_url") or "").lower() + (resolved.get("description") or "").lower())


if __name__ == "__main__":
    unittest.main()
