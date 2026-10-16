from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest

from backend.app_store import AppStoreMonitor


@pytest.fixture
def monitor():
    instance = AppStoreMonitor(storage=None, formatter=None)
    yield instance
    instance.session.close()


@pytest.mark.parametrize(
    "country, expected_country, expected_language",
    [
        ("ru", "ru", "ru"),
        (" DE ", "de", "de"),
        ("fr", "fr", "fr"),
        ("es", "es", "es"),
        ("jp", "jp", "ja"),
        ("br", "br", "pt"),
        ("ua", "ua", "uk"),
        ("us", "us", "en"),
        ("zz", "zz", "en"),
        (None, "us", "en"),
        ("invalid", "us", "en"),
    ],
)
def test_primary_metadata_uses_storefront_language(
    monitor, monkeypatch, country, expected_country, expected_language
):
    scraper = Mock(return_value={
        "version": "2.0",
        "recentChanges": "Localized release notes",
        "updated": 1781827200000,
    })
    monkeypatch.setattr("backend.app_store.play_app", scraper)
    fallback = Mock(side_effect=AssertionError("Unexpected HTML fallback"))
    monkeypatch.setattr(monitor.session, "get", fallback)

    result = monitor.fetch_android_app_info("com.example.app", country)

    scraper.assert_called_once_with(
        "com.example.app", lang=expected_language, country=expected_country
    )
    assert result["releaseNotes"] == "Localized release notes"
    fallback.assert_not_called()


@pytest.mark.parametrize(
    "country, language", [("ru", "ru"), ("de", "de"), ("fr", "fr"), ("es", "es"), ("jp", "ja")]
)
@pytest.mark.parametrize("localized_notes", [None, "Localized release notes"])
def test_english_fallback_parses_notes_and_date_for_localized_storefronts(
    monitor, monkeypatch, country, language, localized_notes
):
    scraper = Mock(return_value={
        "version": "Varies with device",
        "recentChanges": localized_notes,
        "updated": None,
    })
    monkeypatch.setattr("backend.app_store.play_app", scraper)
    fallback = Mock(return_value=SimpleNamespace(
        status_code=200,
        text=(
            '<div>Updated on</div><div class="date">Jun 19, 2026</div>'
            'What\'s new</h2></div></div></header><div class="notes">'
            '<div itemprop="description">Fixes &amp; improvements<br>More fixes</div></div>'
        ),
    ))
    monkeypatch.setattr(monitor.session, "get", fallback)

    result = monitor.fetch_android_app_info("com.example.app", country)

    scraper.assert_called_once_with("com.example.app", lang=language, country=country)
    fallback.assert_called_once()
    args, kwargs = fallback.call_args
    query = parse_qs(urlparse(args[0]).query)
    assert query["hl"] == ["en"]
    assert query["gl"] == [country]
    assert query["id"] == ["com.example.app"]
    assert "_" in query
    assert kwargs["headers"]["Accept-Language"] == "en"
    assert kwargs["headers"]["Cache-Control"] == "no-cache, no-store, max-age=0"
    assert result["releaseNotes"] == (localized_notes or "Fixes & improvements\nMore fixes")
    assert result["updated"] == int(datetime(2026, 6, 19).timestamp() * 1000)
