# Hostel Shift Scheduler

A local Streamlit app that turns employee availability into a hostel rota.

## Current scheduling assumptions

- Front (10:00–19:00): one part-timer, otherwise manager.
- Cleaning (10:00–15:00): preferably two part-timers; one is accepted and no
  assignment is created when nobody is available.
- Night (19:00–10:00 the next morning): one part-timer, otherwise Manager.
- A Night shift belongs to the date on which it starts.
- A person receives at most one shift starting on the same date.
- Mandatory Night and Front roles are filled before Cleaning.
- Assignments are balanced by giving preference to people with fewer shifts.
- Manager receives at least 21 Front or Night shifts per month. For a shorter
  selected date range with fewer than 21 required shifts, all available required
  shifts are assigned to the Manager.
- The app automatically selects at most two cleaners. A third can be added in the
  editable schedule.

## Schedule export and existing workbook

The default export uses sheet `26.09` from `assets/den-reference.xlsx`, based on
the supplied Excel reference. Downloads contain the selected month's sheet with
the reference layout, cell styles, borders and dimensions. Old shifts and dated
notes are cleared before inserting the generated schedule.

Column L (rows 8–28) lists ZAC first, followed by employees from the imported
availability and schedule. ZAC has red cells with white text; other employee
cells are neutral. Column K calculates assigned role combinations in C/F/N order.
Front, Cleaning and Night counts cover all six weekly blocks, including helper
rows. Total, free-stay and remaining-stay formulas extend through row 28. Old
employee notes and used-stay balances are cleared; enter current used stays in S.
ZAC retains the reference's exemption from free-stay calculations.

Exports always use the built-in reference; only availability needs to be uploaded.
Original files are never overwritten. Excel recalculates
formulas when the exported workbook opens. More than 20 employees plus ZAC
requires extending the roster area; export reports this instead of dropping names.

## Availability import (XLSX or CSV)

Download the Excel availability example in the app, or use
`DEN shift availability.csv` as the canonical import example. XLSX imports use the
first worksheet containing recognized availability headers. Formula input cells
use their saved results; recalculate and save in Excel before importing. It is a Google
Forms response export with a `MONTH` column, a `name` column, and daily columns
named `[1日]`, `[2日]`, through `[31日]`. When an employee submits a correction for
the same month, only their latest response is used.

The simpler three-column format is also accepted:

```csv
Employee,Date,Position
Alex,2026-09-01,Front
Alex,2026-09-01,Cleaning
Sam,2026-09-01,Night
```

Use one row per available position. Column capitalization does not matter.

Grid values `C(10-15)`, `F(10-19)`, and `N(19-10)` are converted
automatically. In accordance with the form instructions, Front availability also
counts as Cleaning availability. `CANNOT WORK` is ignored.

## Run locally

Python 3.9 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
streamlit run app.py
```

The terminal will display the local address, normally `http://localhost:8501`.

### Double-click launcher

After completing installation once, macOS users can double-click
`Start DEN Scheduler.command`. Windows users can double-click
`Start DEN Scheduler.bat`. Keep the launcher inside the project folder so it
can locate `app.py` and `.venv` after the folder is moved.

### macOS app launcher

`DEN Scheduler.app` is the preferred launcher for non-technical users. Keep it
inside the project folder, next to `app.py`. It starts Streamlit without showing
a Terminal window and opens `http://localhost:8501` in the default browser.

To rebuild the launcher or refresh its icon on macOS:

```bash
chmod +x packaging/build-macos-app.sh
./packaging/build-macos-app.sh
```

## Test

```bash
python3 -m unittest -v
```
