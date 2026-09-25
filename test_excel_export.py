import unittest
from datetime import date
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from excel_export import reference_schedule_workbook
from scheduler import Assignment, MANAGER


class ExcelExportTests(unittest.TestCase):
    def test_reference_roster_styles_and_six_week_formulas(self):
        reference = Path(__file__).parent / "assets" / "den-reference.xlsx"
        day = date(2027, 5, 31)
        assignments = [Assignment(day, "Front", "Zac"),
                       Assignment(day, "Night", "Alex"),
                       Assignment(day, "Cleaning", "Alex"),
                       Assignment(day, "Cleaning", "Bee"),
                       Assignment(day, "Cleaning", "Cee")]
        with reference.open('rb') as source:
            output = reference_schedule_workbook(source, assignments, day, ['Idle', 'Alex', 'Bee', 'Cee'])
        book = load_workbook(BytesIO(output))
        sheet = book['27.05']
        original = load_workbook(reference)['26.09']
        self.assertEqual(book.sheetnames, ['27.05'])
        self.assertEqual(sheet['L8'].value, 'ZAC')
        self.assertEqual(sheet['L12'].value, 'Idle')
        self.assertEqual(sheet['B48'].value, 'ZAC')
        self.assertEqual(sheet['B54'].value, 'Cee')
        self.assertEqual(sheet['B48'].fill.fgColor.rgb, '00FF0000')
        self.assertEqual(sheet['L9'].fill.fgColor.rgb, '00FFFFFF')
        self.assertEqual(sheet['A3'].style_id, original['A3'].style_id)
        self.assertEqual(sheet.column_dimensions['L'].width, original.column_dimensions['L'].width)
        self.assertEqual(sheet['K9'].value, '=IF(L9="","",IF(O9>0,"C","")&IF(N9>0,"F","")&IF(P9>0,"N",""))')
        for row in range(8,29):
            for col in ('K','M','N','O','P'):
                self.assertEqual(sheet[f'{col}{row}'].data_type, 'f')
            self.assertIn('$B$48:$H$48', sheet[f'N{row}'].value)
            self.assertIn('$B$52:$H$52', sheet[f'O{row}'].value)
            self.assertIn('$B$55:$H$55', sheet[f'P{row}'].value)
        self.assertIsNone(sheet['Q10'].value)
        self.assertIsNone(sheet['S20'].value)
        self.assertEqual(sheet['V8'].value, '=N8*8+P8*6')
        self.assertTrue(book.calculation.fullCalcOnLoad)



if __name__ == "__main__":
    unittest.main()
