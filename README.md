# Natural Numbers Interpretation

Omilia programming assignment. A command-line application that takes a sequence of
recognised numbers (as a speech recogniser would produce them), rebuilds the number,
lists every plausible interpretation of ambiguous number spellings, and checks each
one against the Greek phone number rules.

Both English and Greek speech are taken into account. The default mode follows the
assignment's examples. The `--greek` option adds the one ambiguity that only exists
in Greek: 13–19, where "δεκαπέντε" (15) sounds almost the same as "δέκα πέντε" (10 5).
See [Greek mode](#greek-mode---greek).

## Language and requirements

- **Python 3.9 or newer** (developed and tested with Python 3.13)
- Standard library only — nothing to install, nothing to build

## How to run

From the project folder:

```bash
# Interactive mode: prompts for a sequence, type q to quit
python3 -m natnum

# One-off mode: pass the sequence as arguments
python3 -m natnum 2 10 69 30 6 6 4
```

On Windows use `py -m natnum` or `python -m natnum`.

Options:

- `--greek` also treats 13–19 as ambiguous, for callers speaking Greek (see
  [Greek mode](#greek-mode---greek) below). Works in both modes, e.g.
  `python3 -m natnum --greek 2 10 6 9 30 6 6 4`.
- `--limit N` caps how many interpretations are listed (default 1000; only
  relevant for very long inputs).

### Example

```
$ python3 -m natnum 2 10 69 30 6 6 4
Input:          2 10 69 30 6 6 4
Mode:           default
Number:         2106930664
Phone number:   VALID

Possible interpretations: 4
    #  Output       Digits  Phone number  Read as
  ---------------------------------------------------------
    1  2106930664       10  VALID         2 10 69 30 6 6 4
    2  21060930664      11  INVALID       2 10 60 9 30 6 6 4
    3  210693664         9  INVALID       2 10 69 36 6 4
    4  2106093664       10  VALID         2 10 60 9 36 6 4
```

- **Number / Phone number** — the base level: tokens concatenated as recognised,
  plus the validity check.
- **Possible interpretations** — the advanced level. The literal reading is always
  #1; the rest are ordered by how many merges/splits they apply. "Read as" shows
  how the caller would have grouped the spoken numbers.

## How to run the tests

```bash
python3 -m unittest -v
```

Two test files (about 3 seconds in total, 38 tests):

- `tests/test_natnum.py` covers every example table in the assignment, the phone
  rules, input validation and the CLI.
- `tests/test_properties.py` runs randomised tests with a fixed seed, so any
  failure is reproducible. Random inputs have no hand-written expected answer, so
  these tests check rules that must hold for any input instead:
  - the literal reading is always listed first and there are no duplicate outputs;
  - "Read as" joins back to the output, and every group in it has at most 3 digits;
  - merging and splitting only remove or add zeros, never other digits;
  - the VALID/INVALID label matches an independent regular expression of the rules;
  - random valid phone numbers, spoken in random groupings, always come back VALID.

  These checks run in both the default and Greek modes. The tests also compare the
  app's results with an independent brute-force oracle that tries every possible
  cut of the spoken parts, again in both modes. On top of that, the file adds
  edge cases the brief doesn't cover: zeros, teens (`10 5`, `700 15`), tokens with
  leading zeros, round numbers, and an unambiguous 14-digit number.

## Input rules

- Numbers separated by spaces (extra spaces or tabs are tolerated).
- Each number is 1–3 digits. Anything else is rejected with a message and, in
  interactive mode, the user is asked again.

## Phone number validation

Valid Greek phone numbers, as defined in the assignment:

| Length | Must start with      |
|--------|----------------------|
| 10     | `2` or `69`          |
| 14     | `00302` or `003069`  |

## How ambiguities are found

Every token is broken into the number words a person actually says:

| Token | Spoken parts   |
|-------|----------------|
| `724` | 700 · 20 · 4   |
| `69`  | 60 · 9         |
| `15`  | 15 (one word: "fifteen") |
| `30`  | 30             |
| `0`   | 0              |

All parts of the input form one sequence. An interpretation is any way of grouping
consecutive parts so that each group is something a person could say as one number:

```
[hundreds] + ( [tens] [units] | [teen] | [units] | nothing )
```

That covers both directions of ambiguity in the brief:

- **Merging** — `20 5` may really be "twenty-five" → `25` (as well as `205`);
  `700 24` may be `724`.
- **Splitting** — `75` may really be "seventy, five" → `705` (as well as `75`);
  `724` may also be `70024`, `7204` or `700204`.

Things that are never merged: zeros (`0 0` stays `00`), "ten" plus a digit
in the default mode (`10 5` is not "fifteen"; `--greek` changes this, see below),
two single digits (`6 9` stays `69`), a teen after a
tens word, and tokens with leading zeros such as `05`. Different groupings that
give the same digit string are shown once.

For example 3 of the brief (`0 0 30 69 700 24 1 3 50 2`) this yields 16
interpretations: `69` has 2 readings, `700 24` has 4 and `50 2` has 2. The valid
ones are `00306972413502` (the reading shown in the brief) and `00306972041352`.

## Greek mode (`--greek`)

The callers are giving Greek phone numbers, so they are likely to speak Greek.
Most of the model works the same in Greek as in English:

- tens + units: "είκοσι πέντε" can be `25` or `20 5`, just like "twenty-five";
- hundreds: "επτακόσια είκοσι τέσσερα" can be `724`, `700 24`, `720 4` or `700 20 4`;
- 11 and 12: "έντεκα" and "δώδεκα" are single words, like "eleven" and "twelve".

The difference is 13–19. "Fifteen" sounds nothing like "ten five", but
"δεκαπέντε" (15) and "δέκα πέντε" (10 5) sound almost the same, so a recogniser
could produce either. With `--greek`:

- 13–19 are broken into "δέκα" + digit, so `15` may also be read as `10 5` → `105`;
- `10` followed by a digit 3–9 may be merged, so `10 5` may also be read as `15`;
- `10 1` and `10 2` are never merged, because 11 and 12 are separate words.

**Why it is not the default.** The brief's Example 1 (`2 10 6 9 30 6 6 4`) lists
exactly 2 interpretations. That only holds if `10 6` is never merged into 16, so
the default mode follows the brief. In Greek mode the same input gives 4:

```
$ python3 -m natnum --greek 2 10 6 9 30 6 6 4
...
Possible interpretations: 4
    #  Output      Digits  Phone number  Read as
  --------------------------------------------------------
    1  2106930664      10  VALID         2 10 6 9 30 6 6 4
    2  210693664        9  INVALID       2 10 6 9 36 6 4
    3  216930664        9  INVALID       2 16 9 30 6 6 4
    4  21693664         8  INVALID       2 16 9 36 6 4
```

Greek mode only ever adds readings; every default reading is still listed.

## Project layout

```
natnum/
  core.py      parsing, decomposition into spoken parts, interpretation search
  phone.py     Greek phone number validation
  cli.py       command-line interface (interactive and one-off modes)
  __main__.py  entry point for `python -m natnum`
tests/
  test_natnum.py       examples from the brief, CLI, input validation
  test_properties.py   randomised property tests, brute-force oracle, edge cases
```
