"""Export styled DEN calendars and the availability example as Excel workbooks."""

from collections import defaultdict
from copy import copy
from datetime import date, timedelta
from io import BytesIO, StringIO
import csv

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties


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

    employee_border = Border(**{
        edge: Side(style="thin", color="000000")
        for edge in ("left", "right", "top", "bottom")
    })

    def name_style(cell):
        cell.border = employee_border
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
    sheet['V8'] = '=N8*8+P8*6'
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
