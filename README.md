# Hostel Shift Scheduler

A local Streamlit app that turns employee availability into a hostel rota.

## Current scheduling assumptions

- Front (10:00–19:00): one part-timer, otherwise Zac (manager).
- Cleaning (10:00–15:00): preferably two part-timers; one is accepted and no
  assignment is created when nobody is available.
- Night (19:00–10:00 the next morning): one part-timer, otherwise Zac.
- A Night shift belongs to the date on which it starts.
- A person receives at most one shift starting on the same date.
- Mandatory Night and Front roles are filled before Cleaning.
- Assignments are balanced by giving preference to people with fewer shifts.
- Zac receives at least 21 Front or Night shifts per month. For a shorter
  selected date range with fewer than 21 required shifts, all available required
  shifts are assigned to the Manager.
- The app automatically selects at most two cleaners. A third can be added in the
  editable schedule.

## Schedule export and existing workbook

The included `2026 DEN shift - 26.09.csv` supplies the DEN calendar layout.
From the Export tab, download the generated schedule as a calendar-style `.csv`
named like `2026 DEN shift - 26.10.csv`.

Optionally upload a current `.xlsx` workbook before generation. The app reads its
`front 10-19`, `Clean A`, `Clean B`, and `宿直(19-10)` cells to preserve existing
assignments. The uploaded XLSX source is never overwritten and is not exported.

## Availability CSV

Use `DEN shift availability.csv` as the canonical import example. It is a Google
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
