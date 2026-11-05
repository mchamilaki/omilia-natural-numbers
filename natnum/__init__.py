"""Natural numbers interpretation (Omilia programming assignment)."""

from .core import InputError, Interpretation, interpretations, literal_number, parse_input
from .phone import is_valid_greek_phone

__all__ = [
    "InputError",
    "Interpretation",
    "interpretations",
    "literal_number",
    "parse_input",
    "is_valid_greek_phone",
]
