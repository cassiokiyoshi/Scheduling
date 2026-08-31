"""Create calendar-style CSV exports matching the DEN monthly sheet pattern."""

import csv
from collections import defaultdict
from datetime import date, timedelta
from io import StringIO


def _date_rows(rows):
    return [
        row_index - 1
        for row_index in range(1, len(rows))
        if rows[row_index]
        and str(rows[row_index][0]).strip().casefold() == "front 10-19"
    ]


def _ensure_size(row, size):
    if len(row) < size:
        row.extend([""] * (size - len(row)))


def schedule_calendar_csv(template_bytes, assignments, start_day):
    """Return UTF-8 CSV bytes using the supplied DEN calendar layout."""
    text = template_bytes.decode("utf-8-sig")
    rows = list(csv.reader(StringIO(text)))
    date_rows = _date_rows(rows)
    if len(date_rows) < 5:
        raise ValueError("The CSV does not contain a recognizable DEN calendar layout.")

    width = max(max((len(row) for row in rows), default=0), 8)
    for row in rows:
        _ensure_size(row, width)

    # Clear only calendar dates and entries; preserve labels and the reference
    # file's supporting columns to the right of the weekly grid.
    for date_row in date_rows:
        for row_index in range(date_row, min(date_row + 9, len(rows))):
            for column in range(1, 8):
                rows[row_index][column] = ""

    first_day = date(start_day.year, start_day.month, 1)
    last_day = (
        date(start_day.year + 1, 1, 1) - timedelta(days=1)
        if start_day.month == 12
        else date(start_day.year, start_day.month + 1, 1) - timedelta(days=1)
    )
    locations = {}
    current = first_day
    while current <= last_day:
        week_index = (current.day + first_day.weekday() - 1) // 7
        if week_index >= len(date_rows):
            raise ValueError("The DEN CSV calendar does not have enough weekly rows.")
        column = current.weekday() + 1  # Monday=B through Sunday=H (zero based).
        rows[date_rows[week_index]][column] = f"{current.month}/{current.day}"
        locations[current] = (date_rows[week_index], column)
        current += timedelta(days=1)

    by_day = defaultdict(lambda: defaultdict(list))
    for item in assignments:
        by_day[item.day][item.position].append(item.employee)

    for day, (date_row, column) in locations.items():
        front = by_day[day]["Front"]
        night = by_day[day]["Night"]
        cleaners = by_day[day]["Cleaning"][:2]
        rows[date_row + 1][column] = front[0] if front else ""
        rows[date_row + 5][column] = cleaners[0] if cleaners else ""
        rows[date_row + 6][column] = cleaners[1] if len(cleaners) > 1 else ""
        rows[date_row + 8][column] = night[0] if night else ""

    output = StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    return output.getvalue().encode("utf-8-sig")
