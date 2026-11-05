"""Greek telephone number validation (as defined in the assignment)."""

from __future__ import annotations

# (required length, allowed prefixes)
_RULES = (
    (10, ("2", "69")),
    (14, ("00302", "003069")),
)


def is_valid_greek_phone(number: str) -> bool:
    """True if ``number`` is a valid Greek phone number.

    - 10 digits starting with '2' or '69'
    - 14 digits starting with '00302' or '003069'
    """
    if not number.isdigit():
        return False
    return any(len(number) == length and number.startswith(prefixes) for length, prefixes in _RULES)


def phone_label(number: str) -> str:
    return "VALID" if is_valid_greek_phone(number) else "INVALID"
