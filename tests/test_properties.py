"""Property-based tests on random inputs, plus extra hand-picked edge cases.

Random inputs have no hand-written expected output, so these tests check rules
that must hold for *any* input, and compare the app against an independent
brute-force oracle. A fixed seed keeps every run (and every failure)
reproducible.
"""

import itertools
import random
import re
import unittest

from natnum.core import decompose, interpretations, literal_number, parse_input
from natnum.phone import is_valid_greek_phone

SEED = 20261104
RANDOM_CASES = 1500
ORACLE_CASES = 400

PHONE_RE = re.compile(r"(?:2\d{9}|69\d{8}|00302\d{9}|003069\d{8})")


def random_token(rng):
    """A random 1-3 digit token, biased towards values that create ambiguity."""
    choice = rng.random()
    if choice < 0.25:
        return str(rng.randint(0, 9))
    if choice < 0.45:
        return str(rng.randint(1, 9) * 10)            # round tens: 20, 30, ...
    if choice < 0.65:
        return str(rng.randint(10, 99))
    if choice < 0.75:
        return str(rng.randint(1, 9) * 100)           # round hundreds
    if choice < 0.95:
        return str(rng.randint(100, 999))
    return "0" + str(rng.randint(0, 99)).zfill(rng.choice([1, 2]))[:2]  # leading zero, e.g. "05"


def random_input(rng, max_tokens):
    return [random_token(rng) for _ in range(rng.randint(1, max_tokens))]


def oracle_numbers(tokens):
    """Brute force: try every way to cut the spoken parts, keep the sayable groups.

    A group is sayable iff spelling out its total gives back exactly the same
    words in the same order (e.g. 700+20+4 -> 724 -> 700,20,4). This is written
    independently of natnum.core.is_valid_group.
    """
    parts = [p for i, t in enumerate(tokens) for p in decompose(t, i)]

    def sayable(group):
        if len(group) == 1:
            return True
        if any(p.text is not None or p.value == 0 for p in group):
            return False
        total = sum(p.value for p in group)
        return total <= 999 and [p.value for p in decompose(str(total))] == [p.value for p in group]

    results = set()
    for cuts in itertools.product([False, True], repeat=len(parts) - 1):
        groups, current = [], [parts[0]]
        for part, cut in zip(parts[1:], cuts):
            if cut:
                groups.append(current)
                current = [part]
            else:
                current.append(part)
        groups.append(current)
        if all(sayable(g) for g in groups):
            results.add("".join(str(g[0]) if len(g) == 1 else str(sum(p.value for p in g)) for g in groups))
    return results


class TestRandomProperties(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)

    def cases(self, n, max_tokens):
        for _ in range(n):
            yield random_input(self.rng, max_tokens)

    def test_invariants(self):
        for tokens in self.cases(RANDOM_CASES, 10):
            with self.subTest(tokens=" ".join(tokens)):
                interps = interpretations(parse_input(" ".join(tokens)))
                numbers = [i.number for i in interps]

                # literal reading always present and listed first
                self.assertEqual(numbers[0], literal_number(tokens))
                self.assertEqual(interps[0].edits, 0)
                # no duplicate outputs
                self.assertEqual(len(numbers), len(set(numbers)))
                # after the literal one, ordered by number of merges/splits
                edits = [i.edits for i in interps[1:]]
                self.assertEqual(edits, sorted(edits))
                for it in interps:
                    # output is digits only, and "Read as" joins back to the output
                    self.assertTrue(it.number.isdigit())
                    self.assertEqual("".join(it.reading.split()), it.number)
                    # every group in "Read as" is at most 3 digits
                    self.assertTrue(all(len(g) <= 3 for g in it.groups))
                    # merging only removes digits and splitting only adds zeros,
                    # so dropping every 0 leaves the same digits as the literal reading
                    self.assertEqual(it.number.replace("0", ""), numbers[0].replace("0", ""))

    def test_matches_brute_force_oracle(self):
        # small inputs only: the oracle tries 2^(parts-1) cut patterns
        for tokens in self.cases(ORACLE_CASES, 4):
            with self.subTest(tokens=" ".join(tokens)):
                found = {i.number for i in interpretations(tokens)}
                self.assertEqual(found, oracle_numbers(tokens))

    def test_phone_check_matches_rules(self):
        for tokens in self.cases(RANDOM_CASES, 10):
            for it in interpretations(tokens):
                with self.subTest(number=it.number):
                    self.assertEqual(is_valid_greek_phone(it.number), PHONE_RE.fullmatch(it.number) is not None)

    def test_random_valid_phone_numbers_are_recognised(self):
        # Speak random valid numbers in random digit groupings; the literal
        # reading must always come back VALID.
        for _ in range(500):
            number = self.rng.choice([
                "2" + "".join(self.rng.choices("0123456789", k=9)),
                "69" + "".join(self.rng.choices("0123456789", k=8)),
                "00302" + "".join(self.rng.choices("0123456789", k=9)),
                "003069" + "".join(self.rng.choices("0123456789", k=8)),
            ])
            tokens, rest = [], number
            while rest:
                size = self.rng.randint(1, 3)
                chunk = rest[:size]
                if len(chunk) > 1 and chunk.startswith("0"):
                    chunk = "0"   # people say a leading zero on its own
                tokens.append(chunk)
                rest = rest[len(chunk):]
            with self.subTest(tokens=" ".join(tokens)):
                interps = interpretations(tokens)
                self.assertEqual(interps[0].number, number)
                self.assertTrue(is_valid_greek_phone(interps[0].number))


class TestEdgeCases(unittest.TestCase):
    def numbers(self, text):
        return sorted(i.number for i in interpretations(parse_input(text)))

    def test_zeros(self):
        self.assertEqual(self.numbers("0"), ["0"])
        self.assertEqual(self.numbers("0 0 0"), ["000"])
        self.assertEqual(self.numbers("0 5"), ["05"])        # "zero five" is not five
        self.assertEqual(self.numbers("30 0"), ["300"])      # zero never merges

    def test_teens(self):
        self.assertEqual(self.numbers("10 5"), ["105"])      # "ten five" is not fifteen
        self.assertEqual(self.numbers("15"), ["15"])         # fifteen is one word
        self.assertEqual(self.numbers("20 15"), ["2015"])    # no "twenty fifteen" -> 35
        self.assertEqual(self.numbers("700 15"), ["70015", "715"])
        self.assertEqual(self.numbers("715"), ["70015", "715"])

    def test_leading_zero_token(self):
        self.assertEqual(self.numbers("05"), ["05"])
        self.assertEqual(self.numbers("30 05"), ["3005"])

    def test_round_numbers_are_not_split(self):
        self.assertEqual(self.numbers("30"), ["30"])
        self.assertEqual(self.numbers("400"), ["400"])
        self.assertEqual(self.numbers("410"), ["40010", "410"])  # four hundred | ten

    def test_unambiguous_international_number(self):
        interps = interpretations(parse_input("0 0 3 0 6 9 1 2 3 4 5 6 7 8"))
        self.assertEqual([i.number for i in interps], ["00306912345678"])
        self.assertTrue(is_valid_greek_phone(interps[0].number))

    def test_independent_ambiguities_multiply(self):
        # 69 -> 2 readings, 30 6 -> 2, 700 24 -> 4, 50 2 -> 2
        self.assertEqual(len(interpretations(parse_input("69"))), 2)
        self.assertEqual(len(interpretations(parse_input("69 30 6"))), 4)
        self.assertEqual(len(interpretations(parse_input("69 30 6 700 24 50 2"))), 2 * 2 * 4 * 2)

    def test_max_token_and_mixed_whitespace(self):
        self.assertEqual(self.numbers("999"), sorted(["999", "90099", "9909", "900909"]))
        self.assertEqual(self.numbers(" 2\t10  69 "), self.numbers("2 10 69"))


if __name__ == "__main__":
    unittest.main()
