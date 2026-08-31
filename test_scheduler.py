import unittest
from datetime import date

from scheduler import (
    MANAGER,
    MANAGER_MIN_MONTHLY_SHIFTS,
    Assignment,
    Availability,
    generate_schedule,
    preserve_workbook_assignments,
)


class SchedulerTests(unittest.TestCase):
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
