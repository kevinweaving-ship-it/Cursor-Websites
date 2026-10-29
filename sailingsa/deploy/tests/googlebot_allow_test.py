"""Robots + CIDR builder checks for Google crawl allow-list."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "sailingsa" / "deploy"


def test_robots_allows_og_and_club_logo_not_all_api():
    text = (ROOT / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /api/og/" in text
    assert "Allow: /api/club-logo/" in text
    assert "Disallow: /api/" in text
    assert "Disallow: /profiles" in text
    assert "Sitemap: https://sailingsa.co.za/sitemap.xml" in text


def test_cidr_files_exist_and_look_official():
    geo = (DEPLOY / "nginx-googlebot-cidrs.inc").read_text(encoding="utf-8")
    allow = (DEPLOY / "nginx-sailingsa-googlebot-allow.conf").read_text(encoding="utf-8")
    assert "66.249." in geo or "192.178." in geo
    assert " 1;" in geo
    assert "allow " in allow
    assert geo.count(" 1;") >= 100
    assert allow.count("allow ") >= 100


def test_abuse_conf_skips_googlebot_rate_limits():
    text = (DEPLOY / "nginx-sailingsa-abuse.conf").read_text(encoding="utf-8")
    assert "geo $ssa_googlebot" in text
    assert "limit_req_zone $ssa_limit_ip" in text
    assert "googlebot-cidrs.inc" in text
