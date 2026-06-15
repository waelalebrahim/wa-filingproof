"""Tests for FilingProof. The Number Guard tests are the ones that matter most:
they prove the single promise -- it will not let a wrong number through."""

from filingproof import FilingChecker, FunctionResponder, guard

# A realistic snippet of filing language to verify against.
SOURCE = (
    "Total net sales were $383,285 million in fiscal 2023, compared to "
    "$394,328 million in 2022. The Company's effective tax rate was 14.7%. "
    "Research and development expense was $29.9 billion."
)


# --- Number Guard: the safety net -------------------------------------------

def test_exact_figure_passes():
    assert guard("Net sales were $383,285 million.", SOURCE).ok


def test_percentage_passes():
    assert guard("The effective tax rate was 14.7%.", SOURCE).ok


def test_fabricated_number_is_caught():
    g = guard("Net sales were $500,000 million.", SOURCE)
    assert not g.ok
    assert "$500,000 million" in g.unverified or "500,000 million" in g.unverified


def test_unit_conversion_is_caught():
    # Source says 383,285 million; converting to 383.285 billion must fail.
    g = guard("Net sales were $383.285 billion.", SOURCE)
    assert not g.ok


def test_rounding_is_caught():
    # 14.7% rounded to 15% is not verbatim -> refuse.
    g = guard("The tax rate was about 15%.", SOURCE)
    assert not g.ok


def test_truncation_prefix_is_caught():
    # "$383 million" must NOT match inside "$383,285 million".
    g = guard("Net sales were $383 million.", SOURCE)
    assert not g.ok


def test_wrong_percentage_is_caught():
    g = guard("The effective tax rate was 14.5%.", SOURCE)
    assert not g.ok


def test_bare_count_is_not_guarded():
    # "3 segments" is prose, not a financial figure -> not blocked by the guard.
    assert guard("The company has 3 reportable segments.", SOURCE).ok


def test_billions_phrasing_passes():
    assert guard("R&D expense was $29.9 billion.", SOURCE).ok


# --- FilingChecker: end-to-end with a stand-in responder --------------------

def test_checker_returns_grounded_answer():
    # Responder that quotes the source faithfully -> Answer.
    def faithful(question, passages):
        for i, p in enumerate(passages):
            if "tax rate" in p.lower():
                return i, "The effective tax rate was 14.7%."
        return None

    fc = FilingChecker(FunctionResponder(faithful))
    fc.load(SOURCE)
    result = fc.ask("What was the effective tax rate?")
    assert not result.refused
    assert "14.7%" in result.text
    assert result.quote  # a verbatim source line is attached


def test_checker_refuses_when_not_in_filing():
    fc = FilingChecker(FunctionResponder(lambda q, p: None))
    fc.load(SOURCE)
    result = fc.ask("Who is the CEO's barber?")
    assert result.refused


def test_checker_blocks_a_lying_responder():
    # Even if the model fabricates a number, the Number Guard stops it.
    def liar(question, passages):
        return 0, "Net sales were $999,999 million."

    fc = FilingChecker(FunctionResponder(liar))
    fc.load(SOURCE)
    result = fc.ask("What were net sales?")
    assert result.refused
    assert result.unverified_figures  # tells us which figure failed
