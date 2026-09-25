"""Core scheduling logic for the hostel rota app."""

from dataclasses import dataclass
from datetime import date, timedelta
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


def rest_conflict_pairs(assignments):
    """Indices of same-day doubles and Night-to-next-day daytime shifts."""
    pairs = []
    for i, first in enumerate(assignments):
        if first.employee.casefold() == MANAGER.casefold():
            continue
        for j in range(i + 1, len(assignments)):
            second = assignments[j]
            if first.employee.casefold() != second.employee.casefold():
                continue
            early, late = sorted((first, second), key=lambda item: item.day)
            if early.day == late.day or (
                early.position == "Night"
                and late.position in ("Front", "Cleaning")
                and late.day == early.day + timedelta(days=1)
            ):
                pairs.append((i, j))
    return pairs


def consecutive_shift_keys(assignments):
    return {(assignments[i].day, assignments[i].position, assignments[i].employee)
            for pair in rest_conflict_pairs(assignments) for i in pair}


def _improve_rest(assignments, available):
    """Prefer rested employee cover or swaps; leave manager assignments intact."""
    result = list(assignments)

    def eligible(name, item):
        return name in available.get((item.day, item.position), [])

    def replace(item, name):
        return Assignment(item.day, item.position, name, item.source)

    while True:
        pairs = rest_conflict_pairs(result)
        if not pairs:
            return result
        improved = False
        counts = {}
        for item in result:
            counts[item.employee] = counts.get(item.employee, 0) + 1
        for index in sorted({i for pair in pairs for i in pair}):
            item = result[index]
            candidates = list(available.get((item.day, item.position), []))
            candidates = [name for name in candidates if name.casefold() != MANAGER.casefold()]
            trials = []
            for name in _choose(candidates, counts):
                if name == item.employee:
                    continue
                trial = result.copy()
                trial[index] = replace(item, name)
                trials.append(trial)
            # Swaps can resolve a conflict when a direct replacement is unavailable.
            for other_index, other in enumerate(result):
                if other.employee == item.employee or other.employee.casefold() == MANAGER.casefold():
                    continue
                if eligible(other.employee, item) and eligible(item.employee, other):
                    trial = result.copy()
                    trial[index] = replace(item, other.employee)
                    trial[other_index] = replace(other, item.employee)
                    trials.append(trial)
            for trial in trials:
                trial_pairs = rest_conflict_pairs(trial)
                # Never introduce a new conflict to remove a different one.
                if len(trial_pairs) < len(pairs) and set(trial_pairs).issubset(pairs):
                    result = trial
                    improved = True
                    break
            if improved:
                break
        if not improved:
            return result


def _balance_shift_types(assignments, available):
    """Reduce per-role workload differences without adding rest conflicts."""
    result = list(assignments)
    while True:
        counts = {}
        totals = {}
        for item in result:
            key = (item.employee, item.position)
            counts[key] = counts.get(key, 0) + 1
            totals[item.employee] = totals.get(item.employee, 0) + 1
        before = set(rest_conflict_pairs(result))
        moves = []
        for index, item in enumerate(result):
            if item.employee.casefold() == MANAGER.casefold():
                continue
            for name in set(available.get((item.day, item.position), [])):
                if name.casefold() == MANAGER.casefold():
                    continue
                difference = counts[(item.employee, item.position)] - counts.get((name, item.position), 0)
                if difference <= 1:
                    continue
                moves.append((-difference, totals.get(name, 0) - totals[item.employee],
                              name.casefold(), index, name))
        for _, _, _, index, name in sorted(moves):
            item = result[index]
            trial = result.copy()
            trial[index] = Assignment(item.day, item.position, name, item.source)
            if set(rest_conflict_pairs(trial)).issubset(before):
                result = trial
                break
        else:
            return result


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

    assignments = _improve_rest(assignments, available)
    assignments = _balance_shift_types(assignments, available)
    counts = {}
    for item in assignments:
        if item.employee != MANAGER:
            counts[item.employee] = counts.get(item.employee, 0) + 1
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
