import datetime

WEEKDAY_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def parse_rrule(rrule_str: str) -> dict:
    if not rrule_str:
        return {}
    parts = rrule_str.upper().split(";")
    result = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "FREQ":
            result["freq"] = value
        elif key == "INTERVAL":
            result["interval"] = int(value)
        elif key == "COUNT":
            result["count"] = int(value)
        elif key == "UNTIL":
            result["until"] = datetime.datetime.fromisoformat(value)
        elif key == "BYDAY":
            result["byday"] = [WEEKDAY_MAP[d.strip()] for d in value.split(",") if d.strip() in WEEKDAY_MAP]
    return result


def expand_recurring(base_start: datetime.datetime, base_end: datetime.datetime,
                     rrule_str: str | None,
                     range_start: datetime.datetime, range_end: datetime.datetime) -> list[dict]:
    if not rrule_str:
        return [{"start_time": base_start, "end_time": base_end}]

    config = parse_rrule(rrule_str)
    freq = config.get("freq", "DAILY")
    interval = config.get("interval", 1)
    count = config.get("count")
    until = config.get("until")
    byday = config.get("byday")

    duration = base_end - base_start
    instances = []
    current_start = base_start
    generated = 0

    while current_start <= range_end:
        if until and current_start > until:
            break
        if count is not None and generated >= count:
            break

        if freq == "WEEKLY" and byday:
            week_start = current_start - datetime.timedelta(days=current_start.weekday())
            for day_offset in sorted(byday):
                candidate = week_start + datetime.timedelta(days=day_offset)
                if count is not None and generated >= count:
                    break
                if candidate < range_start or candidate < base_start:
                    continue
                if until and candidate > until:
                    continue
                if candidate > range_end:
                    continue
                instances.append({"start_time": candidate, "end_time": candidate + duration})
                generated += 1
            current_start = week_start + datetime.timedelta(weeks=interval)
        else:
            if current_start >= range_start:
                instances.append({"start_time": current_start, "end_time": current_start + duration})
                generated += 1

            if freq == "DAILY":
                current_start += datetime.timedelta(days=interval)
            elif freq == "WEEKLY":
                current_start += datetime.timedelta(weeks=interval)
            elif freq == "MONTHLY":
                month = current_start.month + interval
                year = current_start.year
                while month > 12:
                    month -= 12
                    year += 1
                try:
                    current_start = current_start.replace(year=year, month=month)
                except ValueError:
                    current_start += datetime.timedelta(days=28 * interval)
            elif freq == "YEARLY":
                current_start = current_start.replace(year=current_start.year + interval)

    return instances
