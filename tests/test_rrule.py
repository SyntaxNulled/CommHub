import datetime
import pytest
from app.rrule import parse_rrule, expand_recurring


class TestParseRRule:
    def test_parse_daily(self):
        result = parse_rrule("FREQ=DAILY;COUNT=5")
        assert result["freq"] == "DAILY"
        assert result["count"] == 5

    def test_parse_weekly_byday(self):
        result = parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=10")
        assert result["freq"] == "WEEKLY"
        assert result["byday"] == [0, 2, 4]
        assert result["count"] == 10

    def test_parse_with_interval(self):
        result = parse_rrule("FREQ=MONTHLY;INTERVAL=3;COUNT=4")
        assert result["freq"] == "MONTHLY"
        assert result["interval"] == 3
        assert result["count"] == 4

    def test_parse_empty_returns_empty(self):
        assert parse_rrule("") == {}

    def test_parse_invalid_key_ignored(self):
        result = parse_rrule("FREQ=DAILY;GARBAGE=xyz;COUNT=5")
        assert result["freq"] == "DAILY"
        assert result["count"] == 5
        assert "garbage" not in result


class TestExpandRecurring:
    def test_no_rrule_returns_single(self):
        start = datetime.datetime(2026, 7, 15, 10, 0)
        end = datetime.datetime(2026, 7, 15, 11, 0)
        result = expand_recurring(start, end, None, datetime.datetime.min, datetime.datetime.max)
        assert len(result) == 1
        assert result[0]["start_time"] == start

    def test_expand_daily_5_occurrences(self):
        base = datetime.datetime(2026, 7, 15, 10, 0)
        result = expand_recurring(base, base + datetime.timedelta(hours=1),
                                  "FREQ=DAILY;COUNT=5",
                                  datetime.datetime.min, datetime.datetime.max)
        assert len(result) == 5
        for i in range(5):
            assert result[i]["start_time"] == base + datetime.timedelta(days=i)

    def test_expand_weekly_byday(self):
        base = datetime.datetime(2026, 7, 15, 10, 0)  # Wednesday
        result = expand_recurring(base, base + datetime.timedelta(hours=1),
                                  "FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=6",
                                  datetime.datetime.min, datetime.datetime.max)
        assert len(result) == 6
        # Should be: Wed Jul 15, Fri Jul 17, Mon Jul 20, Wed Jul 22, Fri Jul 24, Mon Jul 27
        assert result[0]["start_time"].weekday() == 2  # Wednesday
        assert result[1]["start_time"].weekday() == 4  # Friday
        assert result[2]["start_time"].weekday() == 0  # Monday

    def test_expand_respects_date_range(self):
        base = datetime.datetime(2026, 7, 15, 10, 0)
        range_start = datetime.datetime(2026, 7, 17, 0, 0)
        range_end = datetime.datetime(2026, 7, 20, 0, 0)
        result = expand_recurring(base, base + datetime.timedelta(hours=1),
                                  "FREQ=DAILY;COUNT=10",
                                  range_start, range_end)
        for inst in result:
            assert range_start <= inst["start_time"] <= range_end

    def test_expand_until_cutoff(self):
        base = datetime.datetime(2026, 7, 15, 10, 0)
        until = datetime.datetime(2026, 7, 18, 0, 0)
        result = expand_recurring(base, base + datetime.timedelta(hours=1),
                                  f"FREQ=DAILY;UNTIL={until.isoformat()}",
                                  datetime.datetime.min, datetime.datetime.max)
        for inst in result:
            assert inst["start_time"] <= until

    def test_expand_monthly(self):
        base = datetime.datetime(2026, 1, 15, 10, 0)
        result = expand_recurring(base, base + datetime.timedelta(hours=1),
                                  "FREQ=MONTHLY;COUNT=3",
                                  datetime.datetime.min, datetime.datetime.max)
        assert len(result) == 3
        assert result[0]["start_time"].month == 1
        assert result[1]["start_time"].month == 2
        assert result[2]["start_time"].month == 3

    def test_expand_yearly(self):
        base = datetime.datetime(2026, 7, 15, 10, 0)
        result = expand_recurring(base, base + datetime.timedelta(hours=1),
                                  "FREQ=YEARLY;COUNT=2",
                                  datetime.datetime.min, datetime.datetime.max)
        assert len(result) == 2
        assert result[0]["start_time"].year == 2026
        assert result[1]["start_time"].year == 2027
