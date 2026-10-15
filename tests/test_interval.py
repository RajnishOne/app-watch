import pytest
from backend.app import parse_interval, format_interval


def test_parse_interval_valid_units():
    # Hours
    assert parse_interval("1h") == 3600
    assert parse_interval("12h") == 43200
    assert parse_interval(" 6H ") == 21600

    # Minutes
    assert parse_interval("30m") == 1800
    assert parse_interval("15M") == 900

    # Days
    assert parse_interval("1d") == 86400
    assert parse_interval("7D") == 604800

    # Raw seconds
    assert parse_interval("60") == 60
    assert parse_interval("300") == 300


def test_parse_interval_invalid_inputs():
    with pytest.raises(ValueError):
        parse_interval("")

    with pytest.raises(ValueError):
        parse_interval("   ")

    with pytest.raises(ValueError):
        parse_interval("invalid")

    with pytest.raises(ValueError):
        parse_interval("0h")

    with pytest.raises(ValueError):
        parse_interval("-5m")

    with pytest.raises(ValueError):
        parse_interval("1w")


def test_format_interval():
    assert format_interval(86400) == "1d"
    assert format_interval(172800) == "2d"
    assert format_interval(3600) == "1h"
    assert format_interval(7200) == "2h"
    assert format_interval(60) == "1m"
    assert format_interval(120) == "2m"
    assert format_interval(45) == "45s"
