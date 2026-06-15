"""FilingProof — ask a question about one filing; get a grounded answer or a refusal.

Pipeline:
    load filing -> retrieve relevant passages -> responder drafts an answer from
    them (or declines) -> Number Guard verifies every figure -> Answer or Refusal.

The responder is pluggable. Use AnthropicResponder with your API key in
production, or FunctionResponder for tests / custom judges. FilingProof never
shows an answer whose figures it cannot tie to the cited source line.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple, Union

from veritrace.backends import LexicalBackend
from veritrace.sources import SourceDocument, SourceStore

from .models import Answer, Refusal
from .numberguard import guard


class Responder(ABC):
    """Drafts an answer to a question using only the supplied passages.

    Returns (passage_index, answer_text) when the passages support an answer,
    or None when they do not (which becomes a refusal).
    """

    @abstractmethod
    def respond(self, question: str, passages: List[str]) -> Optional[Tuple[int, str]]:
        ...


class FunctionResponder(Responder):
    """Wrap any function as a responder. Used for tests and custom judges."""

    def __init__(self, fn: Callable[[str, List[str]], Optional[Tuple[int, str]]]):
        self._fn = fn

    def respond(self, question, passages):
        return self._fn(question, passages)


_RESPONDER_PROMPT = (
    "You answer questions about a financial filing using ONLY the numbered "
    "passages below. Rules:\n"
    "1. If the passages do not contain the answer, reply exactly: NOT_FOUND\n"
    "2. Never calculate, estimate, convert units, or round. Quote every number "
    "EXACTLY as written in the passage.\n"
    "3. Keep the answer to one or two sentences.\n"
    "Reply with ONLY a JSON object: "
    '{{"passage": <number of the passage you used>, "answer": "<your answer>"}} '
    "or NOT_FOUND.\n\n"
    "PASSAGES:\n{passages}\n\nQUESTION: {question}"
)


class AnthropicResponder(Responder):
    """LLM responder. Pass a complete(prompt)->str callable, or it builds a
    Claude one from veritrace.backends.anthropic_complete (needs ANTHROPIC_API_KEY).
    """

    def __init__(self, complete: Optional[Callable[[str], str]] = None, **kwargs):
        if complete is None:
            from veritrace.backends import anthropic_complete

            complete = anthropic_complete(**kwargs)
        self._complete = complete

    def respond(self, question, passages):
        import json
        import re

        numbered = "\n".join(f"[{i}] {p}" for i, p in enumerate(passages))
        raw = self._complete(
            _RESPONDER_PROMPT.format(passages=numbered, question=question)
        )
        if "NOT_FOUND" in raw and "{" not in raw:
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except ValueError:
            return None
        idx = data.get("passage")
        ans = (data.get("answer") or "").strip()
        if idx is None or not ans:
            return None
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return None
        return idx, ans


class FilingChecker:
    """Loads one filing and answers questions about it, or refuses."""

    def __init__(self, responder: Responder, retrieve_k: int = 6):
        self.responder = responder
        self.retrieve_k = retrieve_k
        self.store = SourceStore()
        self._backend = LexicalBackend()

    def load(self, text: str, name: str = "filing") -> None:
        self.store = SourceStore([SourceDocument(id="filing", text=text, name=name)])

    def ask(self, question: str) -> Union[Answer, Refusal]:
        passages = self.store.passages
        if not passages:
            return Refusal("no filing loaded")

        # Narrow to the most relevant passages so the responder sees a focused set.
        self._backend.index(passages)
        ranked = self._backend.rank(question)[: self.retrieve_k]
        cand_global = [i for i, _ in ranked]
        cand_texts = [passages[i].text for i in cand_global]

        result = self.responder.respond(question, cand_texts)
        if result is None:
            return Refusal("not supported by the filing")

        local_idx, answer_text = result
        if not (0 <= local_idx < len(cand_texts)):
            return Refusal("no valid source citation")

        cited = cand_texts[local_idx]

        # The hard gate: every figure in the answer must be verbatim in the cited
        # source line, or we refuse rather than risk a wrong number.
        g = guard(answer_text, cited)
        if not g.ok:
            return Refusal(
                "a figure could not be verified against the cited source",
                unverified_figures=g.unverified,
            )

        global_idx = cand_global[local_idx]
        return Answer(text=answer_text, quote=cited, location=f"passage {global_idx + 1}")
