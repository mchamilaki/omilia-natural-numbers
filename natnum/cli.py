"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence, TextIO

from .core import InputError, interpretations, literal_number, parse_input
from .phone import phone_label

DEFAULT_LIMIT = 1000
PROMPT = "Enter the number sequence (or 'q' to quit): "


def format_result(tokens: Sequence[str], limit: int = DEFAULT_LIMIT) -> str:
    """Build the report for one input sequence."""
    number = literal_number(tokens)
    lines: List[str] = [
        f"Input:          {' '.join(tokens)}",
        f"Number:         {number}",
        f"Phone number:   {phone_label(number)}",
        "",
    ]

    interps = interpretations(tokens, limit=limit)
    lines.append(f"Possible interpretations: {len(interps)}" + (" (limit reached)" if len(interps) >= limit else ""))

    num_w = max(len("Output"), max(len(i.number) for i in interps))
    head = f"  {'#':>3}  {'Output':<{num_w}}  {'Digits':>6}  {'Phone number':<12}  Read as"
    rows = [
        f"  {k:>3}  {it.number:<{num_w}}  {len(it.number):>6}  {phone_label(it.number):<12}  {it.reading}"
        for k, it in enumerate(interps, start=1)
    ]
    width = max(len(r) for r in rows + [head])
    lines.append(head)
    lines.append("  " + "-" * (width - 2))
    lines.extend(rows)
    return "\n".join(lines)


def run_once(text: str, out: TextIO, limit: int = DEFAULT_LIMIT) -> bool:
    """Process one line of input. Returns False if the input was rejected."""
    try:
        tokens = parse_input(text)
    except InputError as exc:
        print(f"Error: {exc}", file=out)
        return False
    print(format_result(tokens, limit), file=out)
    return True


def interactive(inp: TextIO, out: TextIO, limit: int = DEFAULT_LIMIT) -> int:
    print("Natural numbers interpretation", file=out)
    print("Type numbers of up to 3 digits separated by spaces, e.g. 2 10 69 30 6 6 4", file=out)
    while True:
        out.write("\n" + PROMPT)
        out.flush()
        line = inp.readline()
        if not line:  # EOF
            out.write("\n")
            return 0
        line = line.strip()
        if line.lower() in ("q", "quit", "exit"):
            return 0
        if not line:
            continue
        run_once(line, out, limit)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="natnum",
        description="Interpret a spoken number sequence, list its possible readings "
        "and check each against the Greek phone number rules.",
    )
    parser.add_argument(
        "numbers",
        nargs="*",
        help="the number sequence, e.g. 2 10 69 30 6 6 4. Omit to start interactive mode.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"maximum number of interpretations to list (default {DEFAULT_LIMIT})",
    )
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    if args.numbers:
        return 0 if run_once(" ".join(args.numbers), sys.stdout, args.limit) else 2
    return interactive(sys.stdin, sys.stdout, args.limit)
