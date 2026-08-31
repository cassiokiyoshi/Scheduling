import csv
import unittest
from datetime import date
from io import StringIO

from csv_export import schedule_calendar_csv
from scheduler import Assignment, MANAGER


class CsvExportTests(unittest.TestCase):
    def test_october_export_follows_den_calendar_pattern(self):
        rows = [[""] * 22 for _ in range(56)]
        rows[0][1:8] = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        for date_row in (1, 10, 19, 28, 37, 46):
            rows[date_row + 1][0] = "front 10-19"
            rows[date_row + 5][0] = "Clean A"
            rows[date_row + 6][0] = "Clean B"
            rows[date_row + 8][0] = "宿直(19-10)"
        template = StringIO(newline="")
        csv.writer(template).writerows(rows)
        day = date(2026, 10, 1)

        result = schedule_calendar_csv(
            template.getvalue().encode(),
            [
                Assignment(day, "Front", MANAGER),
                Assignment(day, "Cleaning", "Alex"),
                Assignment(day, "Cleaning", "Jamie"),
                Assignment(day, "Night", MANAGER),
            ],
            day,
        )

        exported = list(csv.reader(StringIO(result.decode("utf-8-sig"))))
        self.assertEqual(exported[1][4], "10/1")
        self.assertEqual(exported[2][4], MANAGER)
        self.assertEqual(exported[6][4], "Alex")
        self.assertEqual(exported[7][4], "Jamie")
        self.assertEqual(exported[9][4], MANAGER)
        self.assertEqual(exported[37][6], "10/31")


if __name__ == "__main__":
    unittest.main()
