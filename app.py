import base64
from calendar import monthrange
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from csv_export import schedule_calendar_csv
from excel_export import read_schedule_workbook
from importer import parse_availability
from scheduler import Assignment, MANAGER, generate_schedule, preserve_workbook_assignments


ICON_PATH = Path(__file__).parent / "assets" / "den-scheduler-icon.webp"
CSV_TEMPLATE_PATH = Path(__file__).parent / "2026 DEN shift - 26.09.csv"
AVAILABILITY_TEMPLATE_PATH = Path(__file__).parent / "DEN shift availability.csv"
ICON_DATA = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
st.set_page_config(page_title="DEN Scheduler", page_icon=Image.open(ICON_PATH), layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"]{background:#f5f5f5}
    [data-testid="stHeader"]{background:transparent}
    [data-testid="stSidebar"]{background:#eeeeee;border-right:1px solid #dcdcdc}
    [data-testid="stSidebarContent"]{padding-top:0!important}
    [data-testid="stSidebarUserContent"]{padding-top:.35rem!important}
    section[data-testid="stSidebar"]>div{padding-top:0!important}
    [data-testid="stSidebarCollapseButton"]{top:.1rem}
    .block-container{max-width:1450px;padding-top:1.2rem;padding-bottom:3rem}
    .sidebar-brand{display:flex;align-items:center;gap:.65rem;margin:0 2.6rem .3rem 0;min-height:42px}
    .sidebar-brand img{width:42px;height:42px;object-fit:cover;border-radius:14%;clip-path:inset(0 round 14%)}
    .sidebar-brand span{font-size:1rem;font-weight:750;color:#1d1d1d;white-space:nowrap}
    .page-intro{font-size:1.5rem;font-weight:700;line-height:1.25;color:#242424;margin:.1rem 0 .8rem}
    .workflow{display:grid;grid-template-columns:repeat(4,1fr);gap:.45rem;margin-bottom:1.2rem}
    .workflow-step{background:#fff;border:1px solid #dfdfdf;border-radius:.6rem;padding:.55rem .65rem;
      color:#555;font-size:.76rem}.workflow-step b{color:#222;margin-right:.28rem}
    .brand{display:flex;align-items:center;gap:.75rem}.logo{width:2.2rem;height:2.2rem;display:grid;
      place-items:center;border-radius:.65rem;color:#fff;background:#363636;font-weight:800}
    .title{font-size:1.55rem;font-weight:750;color:#1d1d1d;letter-spacing:-.03em}
    .subtitle{color:#707070;font-size:.88rem;margin:.2rem 0 1.5rem 2.95rem}
    .step{display:flex;gap:.65rem;align-items:center;padding:.58rem .65rem;margin:.22rem 0;
      border-radius:.6rem;color:#707070;font-size:.82rem}.step.active{background:#dedede;color:#222;font-weight:700}
    .step i{font-style:normal;width:1.35rem;height:1.35rem;display:grid;place-items:center;border-radius:50%;
      border:1px solid #bdbdbd;font-size:.68rem}.step.active i{background:#3d3d3d;border-color:#3d3d3d;color:#fff}
    .local{margin-top:1.3rem;padding-top:1rem;border-top:1px solid #d8d8d8;color:#7b7b7b;font-size:.72rem}
    .heading{color:#1d1d1d;font-size:1.3rem;font-weight:750}.copy{color:#707070;font-size:.84rem;margin:.15rem 0 1rem}
    div[data-testid="stMetric"]{background:#fff;border:1px solid #dfdfdf;padding:.8rem 1rem;border-radius:.75rem}
    .cal{border:1px solid #dfdfdf;border-radius:.8rem;overflow:hidden;background:#fff;margin:.7rem 0 1rem}
    .cal-head,.week{display:grid;grid-template-columns:5rem repeat(7,minmax(5rem,1fr))}
    .cal-head{background:#f8f8f8;border-bottom:1px solid #dfdfdf}.cal-head div{padding:.62rem .3rem;
      text-align:center;color:#797979;font-size:.63rem;font-weight:700;text-transform:uppercase}
    .week{border-bottom:1px solid #e8e8e8}.week:last-child{border-bottom:0}
    .labels{padding:2.3rem .5rem .4rem;background:#fafafa;color:#747474;font-size:.6rem;line-height:1.45rem}
    .day{min-width:0;min-height:8.7rem;padding:.42rem;border-left:1px solid #e8e8e8}.day.out{background:#fafafa}
    .dt{color:#505050;font-size:.68rem;font-weight:750;margin-bottom:.4rem}.dt.out{color:#a7a7a7}
    .shift{height:1.3rem;line-height:1.3rem;padding:0 .34rem;margin-bottom:.15rem;border-radius:.3rem;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:.61rem}
    .front{background:#e8f3ed;color:#236148}.cleaning{background:#ebf0f8;color:#355e97}
    .night{background:#f1ebf7;color:#6c498f}.manager{background:#fff0e3;color:#a8541d}
    .empty{background:#f8e8e9;color:#a5424c;border:1px dashed #dfaeb2}
    @media(max-width:900px){.cal{overflow-x:auto}.cal-head,.week{min-width:750px}}
    @media(max-width:700px){.workflow{grid-template-columns:1fr 1fr}}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f'<style>[data-testid="stSidebarCollapsedControl"]{{background:white url("data:image/webp;base64,{ICON_DATA}") '
    'center/42px 42px no-repeat;width:50px;height:50px;border-radius:.7rem;box-shadow:0 1px 5px rgba(0,0,0,.12);margin:.45rem}}'
    '[data-testid="stSidebarCollapsedControl"] svg{display:none}</style>',
    unsafe_allow_html=True,
)


def schedule_frame(assignments):
    return pd.DataFrame(
        [{"Date": a.day, "Position": a.position, "Employee": a.employee, "Source": a.source} for a in assignments],
        columns=["Date", "Position", "Employee", "Source"],
    )


def end_of_month(day):
    return date(day.year, day.month, monthrange(day.year, day.month)[1])


def assignment_slots(days, assignments, availability):
    assigned = {}
    for item in assignments:
        assigned.setdefault((item.day, item.position), []).append(item.employee)
    available = {}
    for item in availability:
        available.setdefault((item.day, item.position), set()).add(item.employee)

    slots = []
    for day in days:
        front = assigned.get((day, "Front"), [MANAGER])
        cleaners = assigned.get((day, "Cleaning"), [])
        night = assigned.get((day, "Night"), [MANAGER])
        definitions = (
            ("Front", 0, front[0], True),
            ("Cleaning", 0, cleaners[0] if cleaners else "", False),
            ("Cleaning", 1, cleaners[1] if len(cleaners) > 1 else "", False),
            ("Night", 0, night[0], True),
        )
        for position, index, default, required in definitions:
            choices = sorted(available.get((day, position), set()), key=str.casefold)
            choices = ([MANAGER] + choices) if required else ([""] + choices)
            if default not in choices:
                choices.insert(0, default)
            slots.append(
                {
                    "day": day,
                    "position": position,
                    "index": index,
                    "default": default,
                    "required": required,
                    "choices": list(dict.fromkeys(choices)),
                    "key": f"assignment_{day:%Y%m%d}_{position}_{index}",
                }
            )
    return slots


def initialize_assignment_state(slots, signature):
    if st.session_state.get("assignment_signature") != signature:
        for key in list(st.session_state):
            if key.startswith("assignment_") and key != "assignment_signature":
                del st.session_state[key]
        st.session_state.assignment_signature = signature
    for slot in slots:
        if st.session_state.get(slot["key"]) not in slot["choices"]:
            st.session_state[slot["key"]] = slot["default"]


def selected_assignments(slots):
    return [
        Assignment(slot["day"], slot["position"], st.session_state[slot["key"]], "Edited")
        for slot in slots
        if st.session_state.get(slot["key"], "")
    ]


def render_interactive_calendar(days, slots):
    slots_by_day = {}
    for slot in slots:
        slots_by_day.setdefault(slot["day"], []).append(slot)

    styles = [
        'div[data-testid="stVerticalBlockBorderWrapper"]:has(.calendar-day-marker){min-height:10.4rem;',
        'padding:.38rem .42rem!important;border-color:#dfe3df!important;border-radius:.65rem!important}',
        '.calendar-day-marker{height:0;overflow:hidden}',
        'div[class*="st-key-assignment_"] div[data-baseweb="select"]>div{min-height:1.75rem;height:1.75rem;',
        'border:0;border-radius:.32rem;font-size:.68rem;box-shadow:none}',
        'div[class*="st-key-assignment_"] div[data-baseweb="select"]{margin-bottom:.12rem}',
        'div[class*="st-key-assignment_"] svg{width:.8rem;height:.8rem}',
    ]
    for day in days:
        cleaners = [
            st.session_state[slot["key"]]
            for slot in slots_by_day[day]
            if slot["position"] == "Cleaning" and st.session_state[slot["key"]]
        ]
        day_color = "#fdebec" if not cleaners else ("#fff7dc" if len(cleaners) == 1 else "#ffffff")
        styles.append(
            f'.st-key-day_{day:%Y_%m_%d},'
            f'.st-key-day_{day:%Y_%m_%d}[data-testid="stVerticalBlockBorderWrapper"],'
            f'.st-key-day_{day:%Y_%m_%d} div[data-testid="stVerticalBlockBorderWrapper"]'
            f'{{background-color:{day_color}!important}}'
        )
        for slot in slots_by_day[day]:
            current = st.session_state[slot["key"]]
            color = {
                "Front": "#e8f3ed",
                "Cleaning": "#ebf0f8",
                "Night": "#f1ebf7",
            }[slot["position"]]
            if current == MANAGER:
                color = "#fff0e3"
            styles.append(
                f'.st-key-{slot["key"]} div[data-baseweb="select"]>div'
                f'{{background:{color}!important}}'
            )
    st.markdown(f"<style>{''.join(styles)}</style>", unsafe_allow_html=True)

    first, last = min(days), max(days)
    cal_start = first - pd.Timedelta(days=first.weekday())
    cal_end = last + pd.Timedelta(days=6 - last.weekday())
    calendar_days = list(pd.date_range(cal_start, cal_end).date)
    headings = st.columns(7)
    for column, label in zip(headings, ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")):
        column.markdown(f"<div style='text-align:center;color:#777;font-size:.72rem;font-weight:700'>{label}</div>", unsafe_allow_html=True)

    labels = {("Front", 0): "F", ("Cleaning", 0): "CA", ("Cleaning", 1): "CB", ("Night", 0): "N"}
    for offset in range(0, len(calendar_days), 7):
        columns = st.columns(7)
        for column, day in zip(columns, calendar_days[offset : offset + 7]):
            if day < first or day > last:
                column.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            with column.container(key=f"day_{day:%Y_%m_%d}", border=True):
                cleaner_count = sum(
                    1
                    for slot in slots_by_day[day]
                    if slot["position"] == "Cleaning" and st.session_state[slot["key"]]
                )
                shortage_class = "cleaning-none" if cleaner_count == 0 else ("cleaning-one" if cleaner_count == 1 else "cleaning-full")
                st.markdown(
                    f'<div class="calendar-day-marker {shortage_class}"></div>'
                    f'<div style="font-size:.72rem;font-weight:750;margin-bottom:.2rem">{day:%-d %b}</div>',
                    unsafe_allow_html=True,
                )
                for slot in slots_by_day[day]:
                    prefix = labels[(slot["position"], slot["index"])]
                    st.selectbox(
                        f"{prefix} available workers",
                        slot["choices"],
                        key=slot["key"],
                        format_func=lambda value, label=prefix: f"{label} · {value or '—'}",
                        label_visibility="collapsed",
                    )
                selected = [
                    st.session_state[slot["key"]]
                    for slot in slots_by_day[day]
                    if st.session_state[slot["key"]] not in ("", MANAGER)
                ]
                if len(selected) != len(set(selected)):
                    st.warning("Worker assigned twice")


with st.sidebar:
    st.markdown(
        f'<div class="sidebar-brand"><img src="data:image/webp;base64,{ICON_DATA}" alt="DEN icon">'
        '<span>DEN Scheduler</span></div>',
        unsafe_allow_html=True,
    )
    today = date.today()
    current_month = today.replace(day=1)
    next_month = (
        date(today.year + 1, 1, 1)
        if today.month == 12
        else date(today.year, today.month + 1, 1)
    )
    month_options = [
        date(year, month, 1)
        for year in range(today.year, today.year + 7)
        for month in range(1, 13)
        if date(year, month, 1) >= current_month
    ]
    selected_month = st.selectbox(
        "Schedule month",
        month_options,
        index=month_options.index(next_month),
        format_func=lambda value: value.strftime("%B %Y"),
    )
    start_day = selected_month
    end_day = end_of_month(selected_month)
    schedule_workbook = st.file_uploader(
        "Existing schedule workbook (optional)",
        type="xlsx",
        help=(
            "Upload an XLSX workbook only when you want its existing assignments "
            "preserved. The finished schedule is exported as CSV."
        ),
    )
    availability_file = st.file_uploader("Availability CSV", type="csv")
    with st.expander("CSV help"):
        if AVAILABILITY_TEMPLATE_PATH.exists():
            st.download_button(
                "Download availability example",
                AVAILABILITY_TEMPLATE_PATH.read_bytes(),
                "DEN shift availability.csv",
                mime="text/csv",
            )
        st.caption(
            "Use the DEN Google Forms layout with MONTH, name, and daily columns "
            "such as [1日], [2日], and [3日]."
        )
    st.markdown('<div class="local">Files are processed locally. The uploaded workbook is never overwritten.</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="page-intro">Build and review the monthly hostel schedule</div>'
    '<div class="workflow">'
    '<div class="workflow-step"><b>1</b> Import availability</div>'
    '<div class="workflow-step"><b>2</b> Generate schedule</div>'
    '<div class="workflow-step"><b>3</b> Review assignments</div>'
    '<div class="workflow-step"><b>4</b> Export CSV</div>'
    '</div>',
    unsafe_allow_html=True,
)

if availability_file is None:
    st.info("Upload the availability CSV in the sidebar to start this month's schedule.")
elif end_day < start_day:
    st.error("The end date must be on or after the start date.")
else:
    try:
        availability = parse_availability(availability_file, start_day)
        days = list(pd.date_range(start_day, end_day).date)
        assignments, _ = generate_schedule(days, availability)
        preserved_count = 0
        preserved = []
        if schedule_workbook is not None:
            preserved = read_schedule_workbook(schedule_workbook, start_day, end_day)
            preserved_count = len(preserved)
            assignments = preserve_workbook_assignments(
                days, availability, assignments, preserved
            )
        slots = assignment_slots(days, assignments, availability)
        signature = (
            start_day,
            end_day,
            tuple(sorted((item.employee, item.day, item.position) for item in availability)),
            tuple(sorted((item.employee, item.day, item.position) for item in preserved)),
        )
        initialize_assignment_state(slots, signature)
        current_assignments = selected_assignments(slots)
        frame = schedule_frame(current_assignments)
        st.markdown(f'<div class="heading">Review schedule</div><div class="copy">{start_day:%d %B %Y} – {end_day:%d %B %Y} · {len(set(a.employee for a in availability))} employees</div>', unsafe_allow_html=True)
        manager_count = int((frame["Employee"] == MANAGER).sum())
        cleaning_days = set(frame.loc[frame["Position"] == "Cleaning", "Date"])
        m1, m2, m3 = st.columns(3)
        m1.metric("Days scheduled", len(days))
        m2.metric("Manager cover", manager_count)
        m3.metric("Cleaning shortages", len(set(days) - cleaning_days))

        tab_calendar, tab_workload, tab_export = st.tabs(["Calendar", "Workload", "Export"])
        with tab_calendar:
            st.caption("Click an assigned name to choose another worker who is available for that shift.")
            if preserved_count:
                st.info(f"Preserved {preserved_count} existing assignments from the uploaded workbook.")
            render_interactive_calendar(days, slots)
            st.caption("Light red means no cleaner is assigned. Light yellow means only one cleaner is assigned.")
        current_assignments = selected_assignments(slots)
        edited = schedule_frame(current_assignments)
        with tab_workload:
            workload = pd.Series(
                [item.employee for item in current_assignments if item.employee != MANAGER],
                dtype="object",
            ).value_counts()
            if workload.empty:
                st.info("No part-timer assignments yet.")
            else:
                workers = workload.sort_index(key=lambda values: values.str.casefold())
                columns = st.columns(3)
                for index, (employee, shifts) in enumerate(workers.items()):
                    employee_assignments = [
                        item for item in current_assignments if item.employee == employee
                    ]
                    position_counts = {
                        position: sum(
                            item.position == position for item in employee_assignments
                        )
                        for position in ("Front", "Cleaning", "Night")
                    }
                    columns[index % 3].markdown(
                        '<div style="background:#fff;border:1px solid #dfdfdf;border-radius:.75rem;'
                        'padding:.85rem 1rem;margin-bottom:.75rem">'
                        f'<div style="font-weight:750;font-size:.95rem">{escape(employee)}</div>'
                        f'<div style="font-size:1.35rem;font-weight:750;margin:.15rem 0 .4rem">{shifts} shifts</div>'
                        f'<div style="font-size:.78rem;color:#555;line-height:1.55">Front {position_counts["Front"]}<br>'
                        f'Cleaning {position_counts["Cleaning"]}<br>Night {position_counts["Night"]}</div></div>',
                        unsafe_allow_html=True,
                    )
        with tab_export:
            csv_name = f"{start_day:%Y} DEN shift - {start_day:%y.%m}.csv"
            if not CSV_TEMPLATE_PATH.exists():
                st.info("The included DEN CSV template could not be found.")
            else:
                try:
                    csv_content = schedule_calendar_csv(
                        CSV_TEMPLATE_PATH.read_bytes(), current_assignments, start_day
                    )
                    st.download_button(
                        "Download DEN schedule CSV",
                        csv_content,
                        csv_name,
                        mime="text/csv",
                        type="primary",
                        use_container_width=True,
                    )
                    st.success("CSV ready in the DEN monthly calendar format.")
                except ValueError as csv_error:
                    st.warning(
                        "The included CSV does not contain a recognizable DEN calendar. "
                        f"Details: {csv_error}"
                    )
    except Exception as error:
        st.error(f"Could not create the schedule: {error}")
