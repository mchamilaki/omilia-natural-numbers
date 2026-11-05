import io
import subprocess
import sys
import unittest
from pathlib import Path

from natnum.cli import format_result, interactive
from natnum.core import InputError, Kind, decompose, interpretations, is_valid_group, literal_number, parse_input
from natnum.phone import is_valid_greek_phone

ROOT = Path(__file__).resolve().parent.parent


def numbers(text):
    return [i.number for i in interpretations(parse_input(text))]


class TestParsing(unittest.TestCase):
    def test_tokens(self):
        self.assertEqual(parse_input("2 10 69"), ["2", "10", "69"])
        self.assertEqual(parse_input("  2   10\t69 "), ["2", "10", "69"])

    def test_rejects_bad_input(self):
        for bad in ["", "   ", "2 x 4", "2 1000", "-5", "2.5", "２ 3"]:
            with self.subTest(bad=bad), self.assertRaises(InputError):
                parse_input(bad)


class TestBaseLevel(unittest.TestCase):
    """Tables from 'Task' and 'Base Level' in the brief."""

    def test_number_identification(self):
        cases = {
            "30 2 5 58": "302558",
            "2 10 69 30 6 60 4": "21069306604",
            "6 97 400 23 7 40 5": "697400237405",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(literal_number(parse_input(text)), expected)

    def test_phone_validation_examples(self):
        cases = {
            "30 2 5 58": False,
            "2 10 69 30 6 6 4": True,
            "2 10 69 30 6 60 4": False,
            "0 0 30 69 74 0 9 22 52": True,
        }
        for text, valid in cases.items():
            with self.subTest(text=text):
                self.assertEqual(is_valid_greek_phone(literal_number(parse_input(text))), valid)

    def test_phone_rules(self):
        self.assertTrue(is_valid_greek_phone("2101234567"))
        self.assertTrue(is_valid_greek_phone("6912345678"))
        self.assertFalse(is_valid_greek_phone("6812345678"))   # 10 digits, wrong prefix
        self.assertFalse(is_valid_greek_phone("210123456"))    # 9 digits
        self.assertTrue(is_valid_greek_phone("00302101234567"))
        self.assertTrue(is_valid_greek_phone("00306912345678"))
        self.assertFalse(is_valid_greek_phone("00306812345678"))
        self.assertFalse(is_valid_greek_phone("0030210123456"))  # 13 digits
        self.assertFalse(is_valid_greek_phone(""))


class TestAdvancedLevel(unittest.TestCase):
    """Examples from 'Advanced Level' in the brief."""

    def test_example_1(self):
        self.assertEqual(sorted(numbers("2 10 6 9 30 6 6 4")), sorted(["2106930664", "210693664"]))

    def test_example_2(self):
        self.assertEqual(
            sorted(numbers("2 10 69 30 6 6 4")),
            sorted(["2106930664", "210693664", "2106093664", "21060930664"]),
        )

    def test_example_3(self):
        found = numbers("0 0 30 69 700 24 1 3 50 2")
        for expected in ["0030697002413502", "003069700241352", "00306972413502", "00306097241352"]:
            self.assertIn(expected, found)
        self.assertTrue(is_valid_greek_phone("00306972413502"))
        self.assertFalse(is_valid_greek_phone("00306097241352"))
        # 69 -> 2 readings, 700 24 -> 4 readings, 50 2 -> 2 readings
        self.assertEqual(len(found), 16)

    def test_brief_ambiguities(self):
        self.assertEqual(sorted(numbers("20 5")), ["205", "25"])
        self.assertEqual(sorted(numbers("75")), ["705", "75"])

    def test_literal_reading_first(self):
        for text in ["2 10 69 30 6 6 4", "0 0 30 69 700 24 1 3 50 2", "5"]:
            with self.subTest(text=text):
                self.assertEqual(numbers(text)[0], literal_number(parse_input(text)))

    def test_no_duplicates(self):
        found = numbers("0 0 30 69 700 24 1 3 50 2")
        self.assertEqual(len(found), len(set(found)))

    def test_not_ambiguous(self):
        # zeros, teens, round tens, digit pairs and leading-zero tokens stay as they are
        for text in ["0 0", "10 5", "15", "30", "6 9", "05 3", "2 100"]:
            with self.subTest(text=text):
                self.assertEqual(numbers(text), [literal_number(parse_input(text))])

    def test_hundreds(self):
        self.assertEqual(sorted(numbers("724")), sorted(["724", "70024", "7204", "700204"]))
        self.assertEqual(sorted(numbers("700 15")), sorted(["70015", "715"]))
        self.assertEqual(sorted(numbers("100 5")), sorted(["1005", "105"]))

    def test_long_input_is_fine(self):
        found = interpretations(parse_input(" ".join(["21"] * 40)), limit=50)
        self.assertEqual(len(found), 50)


class TestParts(unittest.TestCase):
    def test_decompose(self):
        self.assertEqual([p.value for p in decompose("724")], [700, 20, 4])
        self.assertEqual([p.value for p in decompose("915")], [900, 15])
        self.assertEqual([p.value for p in decompose("409")], [400, 9])
        self.assertEqual([p.kind for p in decompose("0")], [Kind.ZERO])
        self.assertEqual([p.kind for p in decompose("07")], [Kind.LITERAL])

    def test_group_rules(self):
        def g(*tokens):
            parts = [p for t in tokens for p in decompose(t)]
            return is_valid_group(parts)

        self.assertTrue(g("30", "6"))
        self.assertTrue(g("700", "24"))
        self.assertTrue(g("700", "15"))
        self.assertFalse(g("10", "5"))
        self.assertFalse(g("6", "9"))
        self.assertFalse(g("20", "30"))
        self.assertFalse(g("0", "5"))
        self.assertFalse(g("5", "100"))


class TestCli(unittest.TestCase):
    def test_report(self):
        report = format_result(parse_input("2 10 69 30 6 6 4"))
        self.assertIn("Number:         2106930664", report)
        self.assertIn("Phone number:   VALID", report)
        self.assertIn("Possible interpretations: 4", report)
        self.assertIn("2106093664", report)

    def test_interactive_session(self):
        out = io.StringIO()
        interactive(io.StringIO("2 10 6 9 30 6 6 4\nabc\nq\n"), out)
        text = out.getvalue()
        self.assertIn("Possible interpretations: 2", text)
        self.assertIn("Error:", text)

    def test_command_line(self):
        res = subprocess.run(
            [sys.executable, "-m", "natnum", "30", "2", "5", "58"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        self.assertIn("302558", res.stdout)
        bad = subprocess.run([sys.executable, "-m", "natnum", "1234"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
