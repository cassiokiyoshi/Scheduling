"""Availability CSV importers, including the current DEN Google Form layout."""

import csv
import re
import io
from datetime import date, datetime

from scheduler import Availability, POSITIONS


def _read_rows(uploaded_file):
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    content = uploaded_file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    raw_rows = list(csv.reader(io.StringIO(content)))
    header_index = None
    for index, row in enumerate(raw_rows):
        normalized = {str(value).strip().casefold() for value in row}
        has_simple_headers = {"employee", "date", "position"}.issubset(normalized)
        has_form_headers = "name" in normalized and any(
            re.search(r"(?<!\d)([1-9]|[12]\d|3[01])\s*日", str(value))
            for value in row
        )
        if has_simple_headers or has_form_headers:
            header_index = index
            break
    if header_index is None:
        return []

    headers = []
    used = set()
    for column, value in enumerate(raw_rows[header_index], start=1):
        header = str(value).strip() or f"Column {column}"
        original = header
        suffix = 2
        while header in used:
            header = f"{original} ({suffix})"
            suffix += 1
        headers.append(header)
        used.add(header)

    rows = []
    for raw in raw_rows[header_index + 1 :]:
        padded = list(raw) + [""] * (len(headers) - len(raw))
        if any(str(value).strip() for value in padded):
            rows.append(dict(zip(headers, padded[: len(headers)])))
    return rows


def _month_number(value):
    text = str(value or "").strip().casefold()
    match = re.search(r"(?:^|\D)(1[0-2]|[1-9])\s*月", text)
    if match:
        return int(match.group(1))
    names = (
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    )
    return next((index for index, name in enumerate(names, start=1) if name in text), None)


def _parse_date(value):
    value = value.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        for pattern in ("%m/%d/%Y", "%Y/%m/%d", "%m/%d/%y"):
            try:
                return datetime.strptime(value, pattern).date()
            except ValueError:
                pass
    raise ValueError(f"Invalid date: {value}")


def parse_availability(uploaded_file, schedule_start: date) -> list:
    rows = _read_rows(uploaded_file)
    if not rows:
        return []
    columns = list(rows[0].keys())
    normalized = {str(column).strip().lower(): column for column in columns}
    records = set()

    if {"employee", "date", "position"}.issubset(normalized):
        position_lookup = {position.casefold(): position for position in POSITIONS}
        for row_number, row in enumerate(rows, start=2):
            employee = str(row[normalized["employee"]] or "").strip()
            raw_position = str(row[normalized["position"]] or "").strip().casefold()
            if raw_position not in position_lookup:
                raise ValueError(f"Row {row_number}: invalid position")
            if not employee:
                raise ValueError(f"Row {row_number}: employee is empty")
            records.add(Availability(employee, _parse_date(str(row[normalized["date"]] or "")), position_lookup[raw_position]))
        return list(records)

    name_column = normalized.get("name") or normalized.get("employee")
    month_column = normalized.get("month")
    day_columns = {}
    for column in columns:
        match = re.search(r"(?<!\d)([1-9]|[12]\d|3[01])\s*日", str(column))
        if match:
            day_columns[int(match.group(1))] = column
    if name_column is None or not day_columns:
        raise ValueError("Expected Employee/Date/Position columns or a Google Forms export with Name and daily grid columns.")

    token_positions = {"C": ("Cleaning",), "F": ("Front", "Cleaning"), "N": ("Night",)}
    selected_rows = {}
    for row_number, row in enumerate(rows, start=2):
        if month_column is not None:
            submitted_month = _month_number(row.get(month_column))
            if submitted_month is not None and submitted_month != schedule_start.month:
                continue
        employee = str(row[name_column] or "").strip()
        if not employee:
            raise ValueError(f"Row {row_number}: name is empty")
        # Google Forms responses can contain corrections. The export is ordered
        # chronologically, so the last response for an employee/month wins.
        selected_rows[employee.casefold()] = (row_number, employee, row)

    for row_number, employee, row in selected_rows.values():
        for day_number, column in day_columns.items():
            raw = str(row[column] or "").upper()
            if "CANNOT WORK" in raw:
                continue
            try:
                parsed_day = date(schedule_start.year, schedule_start.month, day_number)
            except ValueError:
                continue
            for token, positions in token_positions.items():
                if re.search(rf"(?:^|[,;\s]){token}(?:\(|$)", raw):
                    for position in positions:
                        records.add(Availability(employee, parsed_day, position))
    return list(records)
