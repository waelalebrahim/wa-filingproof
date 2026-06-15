"""Result types: every query returns either an Answer (grounded + quoted) or a Refusal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Answer:
    """A grounded answer. Every figure in `text` was verified against `quote`."""

    text: str
    quote: str            # the verbatim source line(s) the answer rests on
    location: str         # where in the filing (e.g. passage index / section)

    refused = False

    def __str__(self) -> str:
        return f"{self.text}\n  source: \u201c{self.quote}\u201d ({self.location})"


@dataclass
class Refusal:
    """No grounded answer. The honest output when support is missing or unsafe."""

    reason: str
    unverified_figures: Optional[List[str]] = None

    refused = True
    text = "Not stated in this filing."

    def __str__(self) -> str:
        base = f"Not stated in this filing. ({self.reason})"
        if self.unverified_figures:
            base += f" Unverifiable figures: {', '.join(self.unverified_figures)}"
        return base
