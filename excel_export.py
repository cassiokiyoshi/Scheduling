"""Write generated assignments into the hostel's existing monthly workbook layout."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from io import BytesIO
from io import StringIO
import csv
import re
from copy import copy

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.workbook.properties import CalcProperties
from openpyxl.utils import get_column_letter
from csv_export import schedule_calendar_csv

from scheduler import Assignment


def reference_schedule_workbook(workbook_file, assignments, start_day, employee_names):
    """Build a fresh schedule from 26.09, retaining the reference sheet layout."""
    workbook_file.seek(0)
    workbook = load_workbook(workbook_file)
    if "26.09" not in workbook.sheetnames:
        raise ValueError("The reference workbook must contain sheet 26.09.")
    source = workbook["26.09"]
    sheet = workbook.copy_worksheet(source)
    sheet.conditional_formatting = copy(source.conditional_formatting)
    sheet.data_validations = copy(source.data_validations)
    # Export only the requested month; historical schedules remain in the source.
    for other in list(workbook.worksheets):
        if other is not sheet:
            workbook.remove(other)
    sheet.title = _month_sheet_name(start_day)
    date_rows = _calendar_date_rows(sheet)
    if len(date_rows) < 6:
        raise ValueError("The reference needs six weekly calendar blocks.")
    names = {}
    for name in list(employee_names) + [item.employee for item in assignments]:
        if name.strip() and name.strip().casefold() != "zac":
            names.setdefault(name.strip().casefold(), name.strip())
    roster = ["ZAC"] + sorted(names.values(), key=str.casefold)
    if len(roster) > 21:
        raise ValueError("Rows 8–28 have room for ZAC and 20 employees; reduce the roster or extend the template.")

    def name_style(cell):
        manager = str(cell.value or "").casefold() == "zac"
        cell.fill = PatternFill("solid", fgColor="FF0000" if manager else "FFFFFF")
        font = copy(cell.font)
        font.color = "FFFFFF" if manager else "000000"
        cell.font = font

    # Remove prior-month shifts and dated notes, retaining borders and dimensions.
    for date_row in date_rows:
        for row in sheet.iter_rows(min_row=date_row, max_row=date_row + 8, min_col=2, max_col=8):
            for cell in row:
                cell.value = None
        for offset in (1, 2, 5, 6, 7, 8):
            for row in sheet.iter_rows(min_row=date_row + offset, max_row=date_row + offset, min_col=2, max_col=8):
                for cell in row:
                    name_style(cell)
    by_day = defaultdict(lambda: defaultdict(list))
    for item in assignments:
        by_day[item.day][item.position].append("ZAC" if item.employee.casefold() == "zac" else item.employee)
    first = date(start_day.year, start_day.month, 1)
    day = first
    while day.month == first.month:
        row = date_rows[(day.day + first.weekday() - 1) // 7]
        col = day.weekday() + 2
        sheet.cell(row, col, day).number_format = "m/d"
        shifts = by_day[day]
        for position, offsets in (("Front", (1,)), ("Cleaning", (5, 6, 7)), ("Night", (8,))):
            if len(shifts[position]) > len(offsets):
                raise ValueError(f"Too many {position} assignments on {day} for the template.")
            for offset, name in zip(offsets, shifts[position]):
                cell = sheet.cell(row + offset, col, name)
                name_style(cell)
        day += timedelta(days=1)

    for row in range(8, 29):
        # Old notes and stay balances belong to the old employee/month.
        for col in range(11, 23):
            cell = sheet.cell(row, col)
            if row > 25:
                cell._style = copy(sheet.cell(25, col)._style)
            cell.value = None
        sheet.cell(row, 12, roster[row - 8] if row - 8 < len(roster) else None)
        name_style(sheet.cell(row, 12))
        for col, offsets in ((14, (1, 2)), (15, (5, 6, 7)), (16, (8,))):
            terms = [f'COUNTIF($B${base + offset}:$H${base + offset},$L{row})'
                     for base in date_rows for offset in offsets]
            sheet.cell(row, col, f'=IF($L{row}="","",' + '+'.join(terms) + ')')
        sheet.cell(row, 11, f'=IF(L{row}="","",IF(O{row}>0,"C","")&IF(N{row}>0,"F","")&IF(P{row}>0,"N",""))')
        sheet.cell(row, 13, f'=IF(L{row}="","",SUM(N{row}:P{row}))')
        sheet.cell(row, 18, '-' if row == 8 else f'=IF(L{row}="","",QUOTIENT(M{row},4))')
        sheet.cell(row, 20, '-' if row == 8 else f'=IF(L{row}="","",R{row}-S{row})')
    sheet['V8'] = '=N8*8+O8*5+P8*7'
    workbook.calculation = CalcProperties(calcId=0, fullCalcOnLoad=True, forceFullCalc=True)
    workbook.active = 0
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def csv_workbook(template_bytes, sheet_name):
    """Convert a CSV layout to a real workbook, retaining any formula text."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    for row in csv.reader(StringIO(template_bytes.decode("utf-8-sig"))):
        sheet.append(row)
    for cells in sheet.iter_rows():
        for cell in cells:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for column in range(1, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(column)].width = 20
    sheet.column_dimensions["A"].width = 24
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "B2"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def schedule_calendar_xlsx(template_bytes, assignments, start_day):
    """Create an XLSX calendar when no original Excel template is available."""
    return csv_workbook(
        schedule_calendar_csv(template_bytes, assignments, start_day),
        _month_sheet_name(start_day),
    )


def _month_sheet_name(day):
    return f"{day.year % 100:02d}.{day.month:02d}"


def _calendar_date_rows(sheet):
    """Return the date-header rows for each weekly calendar block."""
    rows = []
    for row in range(1, sheet.max_row):
        label = str(sheet.cell(row + 1, 1).value or "").strip().casefold()
        if "front 10-19" in label:
            rows.append(row)
    return rows


def _ensure_month_sheet(workbook, start_day):
    """Create a missing monthly sheet by cloning the latest DEN calendar layout."""
    target_name = _month_sheet_name(start_day)
    if target_name in workbook.sheetnames:
        return workbook[target_name]

    calendar_sheets = [
        sheet for sheet in workbook.worksheets if len(_calendar_date_rows(sheet)) >= 5
    ]
    if not calendar_sheets:
        return None

    source = calendar_sheets[-1]
    sheet = workbook.copy_worksheet(source)
    sheet.title = target_name
    date_rows = _calendar_date_rows(sheet)

    # Clear only the six calendar blocks. Labels, formulas, employee summaries,
    # dimensions, print settings, and visual formatting remain copied intact.
    for date_row in date_rows:
        for row in range(date_row, min(date_row + 9, sheet.max_row + 1)):
            for column in range(2, 9):
                sheet.cell(row, column).value = None

    first_day = date(start_day.year, start_day.month, 1)
    last_day = (
        date(start_day.year + 1, 1, 1) - timedelta(days=1)
        if start_day.month == 12
        else date(start_day.year, start_day.month + 1, 1) - timedelta(days=1)
    )
    current = first_day
    while current <= last_day:
        week_index = (current.day + first_day.weekday() - 1) // 7
        if week_index >= len(date_rows):
            raise ValueError(f"The DEN calendar layout has no room for {target_name}.")
        column = current.weekday() + 2  # Monday=B through Sunday=H.
        sheet.cell(date_rows[week_index], column).value = current
        current += timedelta(days=1)
    return sheet


def _schedule_table_columns(sheet):
    """Return normalized schedule-table columns when the sheet uses that layout."""
    for row in range(1, min(sheet.max_row, 5) + 1):
        columns = {
            str(sheet.cell(row, column).value or "").strip().casefold(): column
            for column in range(1, sheet.max_column + 1)
        }
        if {"date", "position", "employee"}.issubset(columns):
            return row, columns
    return None, None


def _cell_day(value, year, month):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        if value.month != month:
            return None
        try:
            return date(year, month, value.day)
        except ValueError:
            return None
    if not isinstance(value, str):
        return None
    formula_match = re.search(
        r"DATE\s*\(\s*\d{4}\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
        value,
        re.IGNORECASE,
    )
    iso_match = re.search(r"\d{4}\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})", value)
    short_match = re.search(r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})(?!\d)", value)
    japanese_match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?", value)
    match = formula_match or iso_match or japanese_match or short_match
    if not match or int(match.group(1)) != month:
        return None
    try:
        return date(year, month, int(match.group(2)))
    except ValueError:
        return None


def _row_label(sheet, row, date_column):
    values = [sheet.cell(row, column).value for column in range(1, date_column)]
    return " ".join(str(value).strip() for value in values if value is not None).casefold()


def _position_rows(sheet, date_row, date_column):
    found = {}
    for row in range(date_row + 1, min(date_row + 9, sheet.max_row + 1)):
        label = _row_label(sheet, row, date_column)
        if "front 10-19" in label:
            found["Front"] = row
        elif label.startswith("clean a"):
            found["Cleaning A"] = row
        elif label.startswith("clean b"):
            found["Cleaning B"] = row
        elif "宿直" in label or "19-10" in label:
            found["Night"] = row
    return found


def update_schedule_workbook(workbook_file, assignments, start_day):
    """Return an updated XLSX copy while retaining the workbook's existing styling."""
    workbook_file.seek(0)
    raw_workbook = workbook_file.read()
    workbook = load_workbook(BytesIO(raw_workbook), data_only=False)
    values_workbook = load_workbook(BytesIO(raw_workbook), data_only=True)
    created_sheet = _ensure_month_sheet(workbook, start_day)
    if created_sheet is not None and created_sheet.title not in values_workbook.sheetnames:
        _ensure_month_sheet(values_workbook, start_day)
    by_day = defaultdict(lambda: defaultdict(list))
    for item in assignments:
        by_day[item.day][item.position].append(item.employee)

    # The app's own simple table export can also be uploaded as a preservation
    # source. Update that table directly instead of looking for DEN calendar cells.
    for sheet in workbook.worksheets:
        header_row, columns = _schedule_table_columns(sheet)
        if columns:
            if sheet.max_row > header_row:
                sheet.delete_rows(header_row + 1, sheet.max_row - header_row)
            for row_number, item in enumerate(
                sorted(assignments, key=lambda value: (value.day, value.position, value.employee)),
                start=header_row + 1,
            ):
                sheet.cell(row_number, columns["date"]).value = item.day
                sheet.cell(row_number, columns["position"]).value = item.position
                sheet.cell(row_number, columns["employee"]).value = item.employee
                if "source" in columns:
                    sheet.cell(row_number, columns["source"]).value = item.source
                sheet.cell(row_number, columns["date"]).number_format = "yyyy-mm-dd"
            output = BytesIO()
            workbook.save(output)
            return output.getvalue()

    written_days = set()
    for sheet in ([created_sheet] if created_sheet is not None else workbook.worksheets):
        values_sheet = values_workbook[sheet.title]
        for row in range(1, sheet.max_row + 1):
            for column in range(1, sheet.max_column + 1):
                displayed_value = values_sheet.cell(row, column).value
                formula_value = sheet.cell(row, column).value
                day = _cell_day(displayed_value, start_day.year, start_day.month)
                if day is None:
                    day = _cell_day(formula_value, start_day.year, start_day.month)
                if day not in by_day:
                    continue
                rows = _position_rows(sheet, row, column)
                if "Front" not in rows or "Night" not in rows:
                    continue
                sheet.cell(rows["Front"], column).value = by_day[day]["Front"][0]
                sheet.cell(rows["Night"], column).value = by_day[day]["Night"][0]
                cleaners = by_day[day]["Cleaning"][:2]
                if "Cleaning A" in rows:
                    sheet.cell(rows["Cleaning A"], column).value = cleaners[0] if cleaners else None
                if "Cleaning B" in rows:
                    sheet.cell(rows["Cleaning B"], column).value = cleaners[1] if len(cleaners) > 1 else None
                written_days.add(day)

    missing = sorted(set(by_day) - written_days)
    if missing:
        raise ValueError(
            "Could not locate calendar cells for: " + ", ".join(day.isoformat() for day in missing)
        )

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def read_schedule_workbook(workbook_file, start_day, end_day):
    """Read existing primary assignments from the DEN calendar workbook."""
    workbook_file.seek(0)
    workbook = load_workbook(workbook_file, data_only=True, read_only=True)
    assignments = []
    seen_days = set()
    for sheet in workbook.worksheets:
        header_row, columns = _schedule_table_columns(sheet)
        if columns:
            for row in range(header_row + 1, sheet.max_row + 1):
                raw_day = sheet.cell(row, columns["date"]).value
                if isinstance(raw_day, datetime):
                    raw_day = raw_day.date()
                elif isinstance(raw_day, str):
                    try:
                        raw_day = date.fromisoformat(raw_day.strip()[:10])
                    except ValueError:
                        continue
                if not isinstance(raw_day, date) or not (start_day <= raw_day <= end_day):
                    continue
                position = str(sheet.cell(row, columns["position"]).value or "").strip()
                employee = str(sheet.cell(row, columns["employee"]).value or "").strip()
                if position in ("Front", "Cleaning", "Night") and employee:
                    assignments.append(Assignment(raw_day, position, employee, "Workbook"))
            return assignments
        for row in range(1, sheet.max_row + 1):
            for column in range(1, sheet.max_column + 1):
                day = _cell_day(sheet.cell(row, column).value, start_day.year, start_day.month)
                if day is None or not (start_day <= day <= end_day) or day in seen_days:
                    continue
                rows = _position_rows(sheet, row, column)
                if "Front" not in rows or "Night" not in rows:
                    continue
                for position, row_key in (
                    ("Front", "Front"),
                    ("Cleaning", "Cleaning A"),
                    ("Cleaning", "Cleaning B"),
                    ("Night", "Night"),
                ):
                    target_row = rows.get(row_key)
                    value = sheet.cell(target_row, column).value if target_row else None
                    employee = str(value).strip() if value is not None else ""
                    if employee and not employee.startswith("="):
                        assignments.append(Assignment(day, position, employee, "Workbook"))
                seen_days.add(day)
    return assignments
