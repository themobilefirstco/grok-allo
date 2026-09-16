"""Text normalization for prose assertions.

The skills are hand-wrapped English prose containing "Allo". Two things would
otherwise make the contract tests brittle for no good reason:

  * a phrase can break across a line, so `.` in a regex stops matching
  * "Allo".lower() is "allo", which does not contain the substring "allo"

Normalizing collapses whitespace and folds accents, so a test asserts what the
skill *says* rather than how it happens to be wrapped.
"""

import re
import unicodedata


def normalize(text):
    """Lowercase, fold accents to ASCII, and collapse all whitespace to spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded).strip().lower()
