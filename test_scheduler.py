import unittest
from datetime import date

from scheduler import (
    MANAGER,
    MANAGER_MIN_MONTHLY_SHIFTS,
    Assignment,
    Availability,
    generate_schedule,
    consecutive_shift_keys,
    _improve_rest,
    _balance_shift_types,
    preserve_workbook_assignments,
)


class SchedulerTests(unittest.TestCase):
    def test_rest_rules_and_manager_exemption(self):
        first, second = date(2026, 9, 1), date(2026, 9, 2)
        assignments = [Assignment(first, "Night", "A"),
                       Assignment(second, "Cleaning", "A"),
                       Assignment(first, "Front", MANAGER),
                       Assignment(first, "Night", MANAGER),
                       Assignment(second, "Front", MANAGER)]
        keys = consecutive_shift_keys(assignments)
        self.assertEqual(keys, {(first, "Night", "A"), (second, "Cleaning", "A")})
        available = {(second, "Cleaning"): ["A", "B"], (first, "Night"): ["A"]}
        result = _improve_rest(assignments, available)
        self.assertFalse(consecutive_shift_keys(result))
        self.assertEqual(result[1].employee, "B")

    def test_unavoidable_rest_conflict_remains_visible(self):
        first, second = date(2026, 9, 1), date(2026, 9, 2)
        assignments = [Assignment(first, "Night", "A"), Assignment(second, "Cleaning", "A")]
        result = _improve_rest(assignments, {(first, "Night"): ["A"], (second, "Cleaning"): ["A"]})
        self.assertEqual(result, assignments)
        self.assertEqual(len(consecutive_shift_keys(result)), 2)

    def test_same_day_front_night_is_flagged_but_normal_days_are_not(self):
        first, second = date(2026, 9, 1), date(2026, 9, 2)
        self.assertEqual(len(consecutive_shift_keys([
            Assignment(first, "Front", "A"), Assignment(first, "Night", "A")])), 2)
        self.assertFalse(consecutive_shift_keys([
            Assignment(first, "Front", "A"), Assignment(second, "Front", "A")]))

    def test_role_balancing_respects_availability_and_rest(self):
        days = [date(2026, 9, day) for day in range(1, 7)]
        for position in ("Front", "Cleaning", "Night"):
            assignments = [Assignment(day, position, "A") for day in days]
            available = {(day, position): ["A", "B"] for day in days}
            result = _balance_shift_types(assignments, available)
            self.assertEqual(sum(a.employee == "A" for a in result), 3)
            self.assertEqual(sum(a.employee == "B" for a in result), 3)
            self.assertFalse(consecutive_shift_keys(result))

    def test_manager_covers_required_positions(self):
        day = date(2026, 9, 1)
        assignments, _ = generate_schedule([day], [])
        result = {(item.position, item.employee) for item in assignments}
        self.assertIn(("Front", MANAGER), result)
        self.assertIn(("Night", MANAGER), result)
        self.assertFalse(any(item.position == "Cleaning" for item in assignments))

    def test_cleaning_prefers_two_and_employee_is_not_double_booked(self):
        day = date(2026, 9, 1)
        availability = [
            Availability("A", day, "Night"),
            Availability("A", day, "Cleaning"),
            Availability("B", day, "Cleaning"),
            Availability("C", day, "Cleaning"),
        ]
        assignments, _ = generate_schedule([day], availability)
        cleaners = [item.employee for item in assignments if item.position == "Cleaning"]
        self.assertEqual(cleaners, ["B", "C"])

    def test_assignment_counts_balance_over_multiple_days(self):
        days = [date(2026, 9, 1), date(2026, 9, 2)]
        availability = [
            Availability(name, day, "Front") for day in days for name in ("A", "B")
        ]
        assignments, counts = generate_schedule(days, availability)
        front = [item.employee for item in assignments if item.position == "Front"]
        self.assertEqual(front, [MANAGER, MANAGER])
        self.assertEqual(counts, {})

    def test_manager_receives_at_least_monthly_minimum(self):
        days = [date(2026, 9, day) for day in range(1, 31)]
        availability = [
            Availability(name, day, position)
            for day in days
            for position in ("Front", "Night")
            for name in ("A", "B", "C")
        ]

        assignments, counts = generate_schedule(days, availability)

        manager_shifts = [item for item in assignments if item.employee == MANAGER]
        self.assertEqual(len(manager_shifts), MANAGER_MIN_MONTHLY_SHIFTS)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_manager_substitution_backfills_cleaning(self):
        days = [date(2026, 9, day) for day in range(1, 31)]
        availability = []
        for day in days:
            availability.extend(
                [
                    Availability("A", day, "Front"),
                    Availability("A", day, "Cleaning"),
                    Availability("B", day, "Night"),
                ]
            )

        assignments, _ = generate_schedule(days, availability)

        substituted_front_days = []
        for day in days:
            if any(
                item.day == day
                and item.position == "Front"
                and item.employee == MANAGER
                for item in assignments
            ):
                substituted_front_days.append(day)
                self.assertTrue(
                    any(
                        item.day == day
                        and item.position == "Cleaning"
                        and item.employee == "A"
                        for item in assignments
                    )
                )
        self.assertTrue(substituted_front_days)

    def test_existing_workbook_assignment_overrides_generated_shift(self):
        day = date(2026, 9, 1)
        availability = [
            Availability("Alex", day, "Front"),
            Availability("Jamie", day, "Front"),
        ]
        generated = [Assignment(day, "Front", "Alex")]
        preserved = [Assignment(day, "Front", "Jamie", "Workbook")]

        result = preserve_workbook_assignments(
            [day], availability, generated, preserved
        )

        self.assertEqual(result, preserved)


if __name__ == "__main__":
    unittest.main()
