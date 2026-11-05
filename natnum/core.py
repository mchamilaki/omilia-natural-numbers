"""Core logic: parsing the recognised number sequence and finding every
plausible interpretation of it.

How ambiguity is modelled
-------------------------
A speech recogniser turns spoken number words into numeric tokens, but the
way it groups those words is not reliable.  "twenty five" may come out as
``25`` or as ``20 5``; "seven hundred twenty four" may come out as ``724``,
``700 24``, ``720 4`` or ``700 20 4``.

So each input token is first broken down into the *spoken parts* it is made
of, i.e. the individual number words:

    724 -> 700 | 20 | 4        (hundreds, tens, units)
    69  -> 60 | 9              (tens, units)
    15  -> 15                  ("fifteen" is a single word)
    30  -> 30
    0   -> 0

The whole input then becomes one flat sequence of parts.  An interpretation
is any way of splitting that sequence into consecutive groups where each
group could be a single spoken number of up to three digits:

    [hundreds] + ( [tens] [units] | [teen] | [units] )

For example ``30 6`` gives the parts ``30 | 6``, which can be read as
``30 6`` -> "306" or merged into ``36`` -> "36".  ``69`` gives ``60 | 9``,
which can be read as ``69`` -> "69" or split into ``60 9`` -> "609".

The literal reading (tokens exactly as recognised) is always one of the
interpretations and is listed first.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Optional, Sequence, Tuple


class InputError(ValueError):
    """Raised when the user input is not a valid number sequence."""


class Kind(Enum):
    ZERO = "zero"          # 0
    UNIT = "unit"          # 1-9
    TEEN = "teen"          # 10-19 (a single word: "ten", "eleven", ...)
    TENS = "tens"          # 20, 30, ..., 90
    HUNDREDS = "hundreds"  # 100, 200, ..., 900
    LITERAL = "literal"    # a token with leading zeros, e.g. "05"; never merged


@dataclass(frozen=True)
class Part:
    """One spoken number word, plus the index of the input token it came from."""

    value: int
    kind: Kind
    token_index: int
    text: Optional[str] = None  # only used for LITERAL parts

    def __str__(self) -> str:
        return self.text if self.text is not None else str(self.value)


@dataclass(frozen=True)
class Interpretation:
    """One possible reading of the input."""

    groups: Tuple[str, ...]  # the numbers as they would have been spoken
    edits: int               # merges + splits compared with the literal reading

    @property
    def number(self) -> str:
        return "".join(self.groups)

    @property
    def reading(self) -> str:
        return " ".join(self.groups)


MAX_TOKEN_DIGITS = 3


def parse_input(text: str) -> List[str]:
    """Split a line of input into tokens and validate them.

    Tokens are separated by whitespace; each must be 1-3 digits.
    """
    tokens = text.split()
    if not tokens:
        raise InputError("Input is empty. Enter numbers separated by spaces, e.g. 2 10 69 30 6 6 4")
    for tok in tokens:
        if not tok.isdigit() or not tok.isascii():
            raise InputError(f"'{tok}' is not a number. Use digits only, separated by spaces.")
        if len(tok) > MAX_TOKEN_DIGITS:
            raise InputError(f"'{tok}' has {len(tok)} digits; each number may have at most {MAX_TOKEN_DIGITS}.")
    return tokens


def literal_number(tokens: Sequence[str]) -> str:
    """The number exactly as recognised: the tokens concatenated."""
    return "".join(tokens)


def decompose(token: str, token_index: int = 0) -> List[Part]:
    """Break a token into its spoken parts (number words)."""
    if len(token) > 1 and token.startswith("0"):
        # "05", "007": not something a person says as one number, so keep as is.
        return [Part(int(token), Kind.LITERAL, token_index, text=token)]

    n = int(token)
    if n == 0:
        return [Part(0, Kind.ZERO, token_index)]

    parts: List[Part] = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        parts.append(Part(hundreds * 100, Kind.HUNDREDS, token_index))
    if 10 <= rest <= 19:
        parts.append(Part(rest, Kind.TEEN, token_index))
    else:
        tens, units = divmod(rest, 10)
        if tens:
            parts.append(Part(tens * 10, Kind.TENS, token_index))
        if units:
            parts.append(Part(units, Kind.UNIT, token_index))
    return parts


def is_valid_group(parts: Sequence[Part]) -> bool:
    """Can these consecutive parts be one spoken number?

    Allowed shapes: [hundreds] followed by one of
    nothing, [tens], [tens, unit], [teen], [unit].
    """
    if not parts:
        return False
    if len(parts) == 1:
        return True
    kinds = [p.kind for p in parts]
    if Kind.ZERO in kinds or Kind.LITERAL in kinds:
        return False

    i = 0
    if kinds[0] is Kind.HUNDREDS:
        i = 1
    rest = kinds[i:]
    return rest in (
        [],
        [Kind.TENS],
        [Kind.TENS, Kind.UNIT],
        [Kind.TEEN],
        [Kind.UNIT],
    )


def _group_text(parts: Sequence[Part]) -> str:
    if len(parts) == 1:
        return str(parts[0])
    return str(sum(p.value for p in parts))


def _count_edits(parts: Sequence[Part], cuts: Sequence[bool]) -> int:
    """How many merges/splits this grouping applies to the literal reading.

    ``cuts[k]`` says whether there is a group boundary between parts k and k+1.
    In the literal reading there is a boundary exactly between parts that come
    from different input tokens.
    """
    edits = 0
    for k, cut in enumerate(cuts):
        literal_cut = parts[k].token_index != parts[k + 1].token_index
        if cut != literal_cut:
            edits += 1
    return edits


def iter_interpretations(tokens: Sequence[str]) -> Iterator[Interpretation]:
    """Yield every grouping of the spoken parts (may contain duplicate numbers)."""
    parts: List[Part] = []
    for idx, tok in enumerate(tokens):
        parts.extend(decompose(tok, idx))
    n = len(parts)

    # Iterative depth-first search, so long inputs cannot hit the recursion limit.
    # Each stack item: (position, groups so far, cuts so far)
    stack: List[Tuple[int, Tuple[str, ...], Tuple[bool, ...]]] = [(0, (), ())]
    while stack:
        pos, groups, cuts = stack.pop()
        if pos == n:
            yield Interpretation(groups, _count_edits(parts, cuts))
            continue
        # Push longer groups first so the shortest (most literal) pops first.
        for end in range(min(pos + 3, n), pos, -1):
            chunk = parts[pos:end]
            if not is_valid_group(chunk):
                continue
            new_cuts = cuts + (False,) * (end - pos - 1)
            if end < n:
                new_cuts += (True,)
            stack.append((end, groups + (_group_text(chunk),), new_cuts))


def interpretations(tokens: Sequence[str], limit: Optional[int] = None) -> List[Interpretation]:
    """All distinct interpretations, literal reading first, then by number of edits.

    ``limit`` caps how many are collected (a safety net for very long inputs;
    phone numbers produce a handful).
    """
    best: dict = {}  # number -> Interpretation with the fewest edits
    for interp in iter_interpretations(tokens):
        current = best.get(interp.number)
        if current is None or interp.edits < current.edits:
            best[interp.number] = interp
        if limit is not None and len(best) >= limit:
            break

    literal = literal_number(tokens)
    ordered = sorted(best.values(), key=lambda it: (it.number != literal, it.edits))
    return ordered
