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
- Front, Cleaning and Night assignments are balanced separately among available
  employees. Coverage and rest constraints take priority over exact equality.
- Avoid Night followed by Front or Cleaning the next day when another eligible
  employee can cover. Same-day double shifts are also treated as conflicts.
- ZAC is exempt from these rest rules and the employee workload balancing.
- Blue calendar cards and employee selectors mark consecutive-shift conflicts,
  including manual edits. Ordinary work on consecutive dates is not highlighted.
  If no suitable alternative is found, coverage is kept and the conflict is shown.
- ZAC targets at least 152 hours per month: Front counts as 8 hours and Night
  as 6. Night coverage reduces required Front shifts: `ceil((152 - 6 × nights) / 8)`,
  with a minimum of zero. With no nights he needs 19 Front shifts; 2 nights need
  18 Front shifts, 3 nights need 17, and 4 nights need 16. Coverage shortages may
  require extra hours. Short ranges may not contain enough shifts to reach 152.
- The app automatically selects at most two cleaners. A third can be added in the
  editable schedule.

## Excel schedule export

The default export uses sheet `26.09` from `assets/den-reference.xlsx`, based on
the supplied Excel reference. Downloads contain the selected month's sheet with
the reference layout, cell styles, borders and dimensions. Old shifts and dated
notes are cleared before inserting the generated schedule.

Column L (rows 8–28) lists ZAC first, followed by employees from the imported
availability and schedule. ZAC has red cells with white text; other employee
cells are neutral. All employee cells have matching thin black borders on all
four sides, including empty slots and the employee list through row 28. Column K calculates assigned role combinations in C/F/N order.
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

## Standalone macOS app

### Open or share the app

1. Give the recipient `dist/DEN Scheduler.zip` (about 74 MB).
2. Unzip it and move `DEN Scheduler.app` to Applications or another folder.
3. Double-click the app. Allow up to a minute for the bundled runtime to unpack;
   the scheduler opens in the default browser.
4. Select a month, upload availability as XLSX or CSV, review assignments, and
   download the Excel schedule. The reference template is already included.
5. Quit DEN Scheduler from its Dock menu when finished to stop the local server.
   Closing the browser tab alone does not stop the app.

Python, runtime dependencies, and the Excel template are included. The recipient
needs no Python installation, project folder, or internet connection to run it.
The server listens only on this computer and chooses an available local port.

### Compatibility and troubleshooting

- The current build is for **Apple Silicon Macs (M1 and newer)**. Intel Macs and
  Windows require separate builds; this package is not universal.
- Startup, the local server, and Excel export were verified on the build Mac.
  Other macOS versions have not been tested.
- The app is locally ad-hoc signed, not Apple-notarized. Another Mac may require
  approval in macOS security settings before opening it.
- If startup fails, inspect `~/Library/Logs/DEN Scheduler/standalone.log`.

### Build from source

First install the development environment using the “Run locally” instructions.
Then run on macOS with Apple command-line tools available:

```bash
.venv/bin/python -m pip install 'pyinstaller>=6,<7'
./packaging/build-macos-app.sh
```

The script bundles the runtime with PyInstaller, compiles the macOS launcher,
adds the icon and Excel reference, signs the app locally, and produces:

- `dist/DEN Scheduler.app` — the standalone application bundle.
- `dist/DEN Scheduler.zip` — the single-file archive for sharing.

`build/` and `dist/` are generated and excluded from Git. Cloning the repository
provides the source and build scripts; build the app locally or obtain the ZIP
separately. Rebuild after source or template changes to include them in the app.

To check the packaged runtime and Excel export without opening the browser:

```bash
"dist/DEN Scheduler.app/Contents/Resources/den-scheduler" --self-test
```

## Test

```bash
python3 -m unittest -v
```
