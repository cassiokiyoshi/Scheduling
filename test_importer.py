import unittest
from datetime import date
from io import StringIO

from importer import parse_availability
from scheduler import Availability


class ImporterTests(unittest.TestCase):
    def test_google_forms_grid_and_front_implies_cleaning(self):
        source = StringIO(
            "name,MONTH,Availability [1日],Availability [2日],How many shifts do you want?\n"
            'Alex,September,"F(10-19), N(19-10)",CANNOT WORK,8\n'
        )
        result = set(parse_availability(source, date(2026, 9, 1)))
        positions = {item.position for item in result if item.day == date(2026, 9, 1)}
        self.assertEqual(positions, {"Front", "Cleaning", "Night"})
        self.assertFalse(any(item.day == date(2026, 9, 2) for item in result))

    def test_real_sheet_layout_detects_second_row_header_and_filters_month(self):
        source = StringIO(
            ",,,,,,\n"
            "タイムスタンプ,MONTH,name,How many shifts do you want?,Column 36, [1日], [2日]\n"
            '2026/08/01,August (8月）,Alex,,8,"F(10-19)",CANNOT WORK\n'
            '2026/09/01,September（9月）,Jamie,,9,"C(10-15)",N(19-10)\n'
        )
        result = set(parse_availability(source, date(2026, 9, 1)))
        self.assertEqual({item.employee for item in result}, {"Jamie"})
        self.assertIn(Availability("Jamie", date(2026, 9, 1), "Cleaning"), result)
        self.assertIn(Availability("Jamie", date(2026, 9, 2), "Night"), result)

    def test_latest_form_submission_replaces_earlier_answer(self):
        source = StringIO(
            "name,MONTH,Availability [1日],Availability [2日]\n"
            'Alex,September,"F(10-19)",CANNOT WORK\n'
            'Alex,September,CANNOT WORK,"N(19-10)"\n'
        )

        result = set(parse_availability(source, date(2026, 9, 1)))

        self.assertFalse(any(item.day == date(2026, 9, 1) for item in result))
        self.assertEqual(
            {item.position for item in result if item.day == date(2026, 9, 2)},
            {"Night"},
        )


if __name__ == "__main__":
    unittest.main()
