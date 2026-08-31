"""Core scheduling logic for the hostel rota app."""

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


POSITIONS = ("Front", "Cleaning", "Night")
MANAGER = "Zac"
MANAGER_MIN_MONTHLY_SHIFTS = 21


@dataclass(frozen=True)
class Availability:
    employee: str
    day: date
    position: str


@dataclass(frozen=True)
class Assignment:
    day: date
    position: str
    employee: str
    source: str = "Automatic"


def _choose(candidates: Iterable[str], counts: Mapping[str, int]) -> List[str]:
    """Return candidates in a deterministic, fair order."""
    return sorted(set(candidates), key=lambda name: (counts.get(name, 0), name.casefold()))


def generate_schedule(
    days: Sequence[date], availability: Sequence[Availability]
) -> Tuple[List[Assignment], Dict[str, int]]:
    """Generate a fair schedule using the documented minimum staffing rules.

    One employee can only hold one shift starting on a given date. Night shifts are
    associated with the date on which they start. Cleaning gets up to two people by
    default; the third available person remains unassigned for manual selection.
    """
    available: Dict[Tuple[date, str], List[str]] = {}
    for item in availability:
        if item.position not in POSITIONS:
            raise ValueError(f"Unknown position: {item.position}")
        available.setdefault((item.day, item.position), []).append(item.employee)

    counts: Dict[str, int] = {}
    assignments: List[Assignment] = []

    for day in sorted(set(days)):
        used_today = set()

        # Fill the mandatory single-person shifts first.
        for position in ("Night", "Front"):
            candidates = [
                name
                for name in available.get((day, position), [])
                if name not in used_today
            ]
            ordered = _choose(candidates, counts)
            chosen = ordered[0] if ordered else MANAGER
            assignments.append(Assignment(day, position, chosen))
            if chosen != MANAGER:
                used_today.add(chosen)
                counts[chosen] = counts.get(chosen, 0) + 1

        # Two cleaners is the target. One is acceptable and three can be added manually.
        candidates = [
            name
            for name in available.get((day, "Cleaning"), [])
            if name not in used_today
        ]
        for chosen in _choose(candidates, counts)[:2]:
            assignments.append(Assignment(day, "Cleaning", chosen))
            used_today.add(chosen)
            counts[chosen] = counts.get(chosen, 0) + 1

    # Manager fallback cover may not reach their monthly minimum when employee
    # availability is high. Replace required-role assignments held by the most
    # heavily scheduled employees until the minimum is met. Short date ranges
    # with fewer than 21 required shifts simply assign every available one.
    manager_count = sum(item.employee == MANAGER for item in assignments)
    while manager_count < MANAGER_MIN_MONTHLY_SHIFTS:
        replaceable = [
            (index, item)
            for index, item in enumerate(assignments)
            if item.position in ("Night", "Front") and item.employee != MANAGER
        ]
        if not replaceable:
            break
        index, item = min(
            replaceable,
            key=lambda pair: (
                -counts.get(pair[1].employee, 0),
                pair[1].day,
                pair[1].position,
                pair[1].employee.casefold(),
            ),
        )
        assignments[index] = Assignment(item.day, item.position, MANAGER)
        counts[item.employee] -= 1
        if counts[item.employee] == 0:
            del counts[item.employee]
        manager_count += 1

    # Refill Cleaning after manager substitutions. A substitution can free a
    # Front-qualified employee who is also eligible for Cleaning.
    for day in sorted(set(days)):
        used_today = {
            item.employee
            for item in assignments
            if item.day == day and item.employee != MANAGER
        }
        cleaner_count = sum(
            item.day == day and item.position == "Cleaning" for item in assignments
        )
        candidates = [
            name
            for name in available.get((day, "Cleaning"), [])
            if name not in used_today
        ]
        for chosen in _choose(candidates, counts)[: max(0, 2 - cleaner_count)]:
            assignments.append(Assignment(day, "Cleaning", chosen))
            used_today.add(chosen)
            counts[chosen] = counts.get(chosen, 0) + 1

    return assignments, counts


def preserve_workbook_assignments(days, availability, generated, preserved):
    """Overlay existing workbook decisions and fill remaining slots safely."""
    valid_days = set(days)
    result = []
    used = {}
    filled = {}

    for item in preserved:
        if item.day not in valid_days or item.position not in POSITIONS:
            continue
        key = (item.day, item.position)
        limit = 2 if item.position == "Cleaning" else 1
        if filled.get(key, 0) >= limit:
            continue
        result.append(item)
        filled[key] = filled.get(key, 0) + 1
        if item.employee != MANAGER:
            used.setdefault(item.day, set()).add(item.employee)

    available = {}
    for item in availability:
        available.setdefault((item.day, item.position), set()).add(item.employee)

    for item in generated:
        key = (item.day, item.position)
        limit = 2 if item.position == "Cleaning" else 1
        if filled.get(key, 0) >= limit:
            continue
        employee = item.employee
        day_used = used.setdefault(item.day, set())
        if employee != MANAGER and employee in day_used:
            alternatives = sorted(
                available.get(key, set()) - day_used,
                key=str.casefold,
            )
            if alternatives:
                employee = alternatives[0]
            elif item.position in ("Front", "Night"):
                employee = MANAGER
            else:
                continue
        result.append(Assignment(item.day, item.position, employee, item.source))
        filled[key] = filled.get(key, 0) + 1
        if employee != MANAGER:
            day_used.add(employee)
    return result
