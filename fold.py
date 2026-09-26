"""ASCII folding for the text mirror."""

import re
import unicodedata

FOLD = {
    "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",  # dashes, quotes
    "\u201c": '"', "\u201d": '"', "\u00ab": '"', "\u00bb": '"',
    "\u00b7": "-", "\u2197": "", "\u2026": "...", "\u2192": "->",  # middle dot, arrows
    "\u0153": "oe", "\u0152": "OE", "\u00e6": "ae", "\u00c6": "AE",
    "\u00a0": " ", "\u202f": " ", "\u00d7": "x",
}


def to_ascii(s, squeeze=True):
    """Fold to ASCII. `squeeze` merges runs of spaces - right for prose,
    wrong for code, where spacing is meaning."""
    for a, b in FOLD.items():
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r" +", " ", s) if squeeze else s
