"""The Number Guard.

FilingProof's one promise is: it will not make up a number. The Number Guard is
how that promise is kept. Before any answer is shown, every financial figure in
it must appear *verbatim* in the cited source text -- with the same sign. If even
one does not, the answer is refused -- not shown.

This is deterministic. No model, no API. It is the last line of defense, and it
errs on the side of refusing: a correct number formatted differently from the
source will be rejected (mildly annoying) rather than a converted, re-signed, or
invented number slipping through (fatal).

Sign awareness
--------------
Financial statements write a negative value in parentheses: a loss of 1,234 is
shown as "(1,234)". A figure stated without that sign is a *different* number --
a net loss reported as positive income is as fatal as a fabricated figure. So the
guard treats the sign as part of the figure: a positive claim must match a
positive occurrence in the source, and a negative claim must match a parenthesised
(or minus-signed) occurrence. A sign that does not match is refused.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

# A "material" figure: something that looks like a financial number, not an
# incidental count. We guard a number token if it carries any of these markers:
#   - a decimal point         3.5
#   - a thousands separator    1,234
#   - a percent sign           5.5%
#   - a currency symbol        $1.2
#   - an adjacent scale word   4 billion / 4M / 4bn
# A bare small integer ("3 segments") is treated as prose and not guarded; this
# is a documented limitation, see README.
_SCALE = r"(?:k|m|bn|b|mn|mm|thousand|million|billion|trillion)"
_CURRENCY = r"[$€£¥]"
_MINUS = ("-", "\u2212")  # hyphen-minus and the unicode minus sign

# Capture a number core plus its surrounding financial markers.
_FIGURE = re.compile(
    rf"""
    (?P<cur>{_CURRENCY})?\s?
    (?P<core>\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?   # 1,234 or 1,234.56
            |\d+\.\d+                            # 3.5
            |\d+)                                # 12
    (?:\s?(?P<pct>%)|\s?(?P<scale>{_SCALE})\b)?  # optional unit, bound to number
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass
class GuardResult:
    ok: bool
    unverified: List[str]  # figures present in the answer but not found in source

    def __bool__(self) -> bool:
        return self.ok


def _normalize(s: str) -> str:
    """Lowercase and collapse whitespace, so '$ 1,234' matches '$1,234'.

    Parentheses and minus signs are preserved -- they carry the sign.
    """
    return re.sub(r"\s+", " ", s.lower()).strip()


def _is_material(m: re.Match) -> bool:
    core = m.group("core")
    has_marker = bool(
        m.group("cur") or m.group("pct") or m.group("scale")
        or "," in core or "." in core
    )
    return has_marker


def _is_negative(text: str, start: int, end: int) -> bool:
    """Is the figure spanning [start, end) in `text` shown as a negative?

    Negative if it is wrapped in parentheses -- "(1,234)" -- which is how filings
    write a loss, or if it is directly preceded by a minus sign -- "-1,234". A
    leading currency symbol between the bracket and the number is tolerated.
    """
    before = text[:start].rstrip()
    if before[-1:] in _MINUS:
        return True
    after = text[end:].lstrip()
    if before[-1:] == "(" and after[:1] == ")":
        return True
    return False


def extract_figures(text: str) -> List[str]:
    """Return the material financial figures found in `text`, as written."""
    figures = []
    for m in _FIGURE.finditer(text):
        if _is_material(m):
            figures.append(m.group(0).strip())
    return figures


def _present(m: re.Match, answer: str, source_norm: str) -> bool:
    """Is this figure standalone-verbatim AND same-signed in the source?

    Uses numeric boundaries so a token is never matched as a *prefix* of a longer
    number: '$383' must not match inside '$383.285 billion' (that would let a
    rounded/truncated figure slip through). Currency, percent, and scale markers
    present in the answer must also be present in the source. The exact digits,
    commas, and decimals must match as written -- this is what defeats unit
    conversions and rounding. Finally, the sign must match: a positive claim only
    verifies against a positive occurrence, a negative claim only against a
    parenthesised/minus-signed one.
    """
    cur = (m.group("cur") or "").lower()
    core = m.group("core").lower()
    pct = m.group("pct") or ""
    scale = (m.group("scale") or "").lower()
    answer_negative = _is_negative(answer, m.start(), m.end())

    no_number_before = r"(?<![\d.,])"
    body = no_number_before
    if cur:
        body += re.escape(cur) + r"\s?"
    body += re.escape(core)
    if pct:
        body += r"\s?" + re.escape(pct)
    elif scale:
        body += r"\s?" + re.escape(scale) + r"\b"
    else:
        # bare core (had a comma/decimal/currency to be material): ensure it is
        # not the prefix of a longer number. A following digit, or a '.'/',' that
        # itself precedes a digit, means the number continues (e.g. 2,876 inside
        # 2,876.50 or 2,876,000) -> reject. A bare '.' or ',' that ends a clause
        # (e.g. "...was 2,876.") is punctuation, not part of the number -> allow.
        body += r"(?!\d)(?![.,]\d)"

    # An occurrence verifies only if its sign matches the answer's sign.
    for sm in re.finditer(body, source_norm):
        if _is_negative(source_norm, sm.start(), sm.end()) == answer_negative:
            return True
    return False


def guard(answer: str, source: str) -> GuardResult:
    """Check every material figure in `answer` against `source`.

    Returns GuardResult(ok=True, []) only if every material figure is standalone-
    verbatim AND same-signed in source. Otherwise ok=False with the offending
    figures listed.
    """
    source_norm = _normalize(source)
    unverified = []
    for m in _FIGURE.finditer(answer):
        if _is_material(m) and not _present(m, answer, source_norm):
            unverified.append(m.group(0).strip())
    return GuardResult(ok=not unverified, unverified=unverified)
