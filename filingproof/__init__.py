"""FilingProof — a fact-checker for financial filings that won't make up a number.

Answers questions about one filing using only that document, quotes the exact
line, and refuses (instead of guessing) when support is missing. Every figure is
verified verbatim against the source by the Number Guard before it is shown.

Built on the VeriTrace engine. Free and open source (MIT).
Author: Wael Alebrahim
"""

from __future__ import annotations

from .checker import AnthropicResponder, FilingChecker, FunctionResponder, Responder
from .models import Answer, Refusal
from .numberguard import GuardResult, extract_figures, guard

__version__ = "0.1.0"
__author__ = "Wael Alebrahim"
__all__ = [
    "FilingChecker",
    "Responder",
    "FunctionResponder",
    "AnthropicResponder",
    "Answer",
    "Refusal",
    "guard",
    "extract_figures",
    "GuardResult",
    "__version__",
]
