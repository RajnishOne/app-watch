import pytest
from backend.formatter import DiscordFormatter


def test_default_formatter_recognizes_fix_and_improvement():
    release_notes = """
New:
- Lidarr: Music artist, album & profile support.
- Overseerr: Manage requests & approvals in-app.

Improvement:
- Accurate notification deep linking.
- Radarr/Sonarr: Cleaner action layout.

Fix:
- Robust TV show data loading.
- Reliable iOS notification tokens.
"""
    formatter = DiscordFormatter()
    formatted = formatter.format_release_notes("2.8.3", release_notes)

    # Check headers are outputted using default formatting ##
    assert "## New" in formatted
    assert "## Improvements" in formatted
    # "Fix" should be normalized to "Fixed" by default
    assert "## Fixed" in formatted

    # Check bullet items are preserved
    assert "- Lidarr: Music artist, album & profile support." in formatted
    assert "- Accurate notification deep linking." in formatted
    assert "- Robust TV show data loading." in formatted


def test_custom_section_names_in_normalization():
    release_notes = """
New:
- Element A

Improvement:
- Element B

Fix:
- Element C
"""
    settings = {
        "message_format_normalize_headers": True,
        "message_format_name_new": "✨ New Features",
        "message_format_name_improvements": "⚡ Improvements",
        "message_format_name_fixed": "🐛 Bug Fixes",
    }
    formatter = DiscordFormatter(settings)
    formatted = formatter.format_release_notes("2.8.3", release_notes)

    assert "## ✨ New Features" in formatted
    assert "## ⚡ Improvements" in formatted
    assert "## 🐛 Bug Fixes" in formatted
    assert "- Element A" in formatted
    assert "- Element B" in formatted
    assert "- Element C" in formatted


def test_disabled_normalization_uses_original_header():
    release_notes = """
New:
- Element A

Improvement:
- Element B

Fix:
- Element C
"""
    settings = {
        "message_format_normalize_headers": False,
    }
    formatter = DiscordFormatter(settings)
    formatted = formatter.format_release_notes("2.8.3", release_notes)

    assert "## New" in formatted
    # Improvement has no trailing s
    assert "## Improvement" in formatted
    # Fix is exactly Fix
    assert "## Fix" in formatted


def test_custom_headers_parsing():
    release_notes = """
Security:
- Fixed security vulnerability

Performance:
- Improved loading time by 50%
"""
    settings = {
        "message_format_custom_headers": "Security, Performance",
        "message_format_normalize_headers": True,
    }
    formatter = DiscordFormatter(settings)
    formatted = formatter.format_release_notes("2.8.3", release_notes)

    assert "## Security" in formatted
    assert "## Performance" in formatted
    assert "- Fixed security vulnerability" in formatted
    assert "- Improved loading time by 50%" in formatted


def test_user_screenshot_case_with_fix_heading():
    release_notes = """
New
- Lidarr: Music artist, album & profile support.
- Overseerr: Manage requests & approvals in-app.
- TV Shows: "Similar Shows" & scroll memory.

Improvement
- Accurate notification deep linking.
- Radarr/Sonarr: Cleaner action layout.
- Setup: Custom HTTP headers & unified help.
- Sharper artwork & TMDB attribution screen.

Fix
- Robust TV show data loading.
- Reliable iOS notification tokens.
- Graceful network error handling.
"""
    # Test default mapping
    formatter = DiscordFormatter()
    formatted = formatter.format_release_notes("2.8.3", release_notes)

    # Defaults normalize New -> New, Improvement -> Improvements, Fix -> Fixed
    assert "## New" in formatted
    assert "## Improvements" in formatted
    assert "## Fixed" in formatted
    
    # Test case when normalization is disabled
    formatter_raw = DiscordFormatter({"message_format_normalize_headers": False})
    formatted_raw = formatter_raw.format_release_notes("2.8.3", release_notes)

    assert "## New" in formatted_raw
    assert "## Improvement" in formatted_raw
    assert "## Fix" in formatted_raw
