# FilingProof — V1 Specification

> A free fact-checker for financial filings. Ask a question about a filing you
> give it; it answers **only** from that document, quotes the exact line, and
> says **"not in this filing"** instead of guessing. It never restates a number
> in its own words, and it never does math.
>
> The I Don't Know Project, pointed at SEC filings. Built on the VeriTrace engine.

**Working name:** FilingProof · **Repo:** `wa-filingproof` · **License:** MIT · **Author:** Wael Alebrahim

---

## The one promise

> **It will not make up a number.**

Everything in this spec exists to keep that single promise. The promise *is* the
product — in finance, a tool that fabricates one figure is finished. So the
design is built around refusing rather than risking a wrong number.

---

## What V1 DOES

1. **Takes one filing the user provides** — a 10-K, 10-Q, earnings transcript, or
   prospectus (pasted text or an uploaded file).
2. **Answers specific questions about that one document only.**
3. **Quotes the supporting line verbatim** for every answer, with its location,
   so the user verifies at a glance.
4. **Refuses by default.** When the answer is not in the document, it says
   "Not stated in this filing" and stops. Refusal is the normal path, not an edge case.
5. **Reuses VeriTrace tiering:** found-and-cited, or not-found. No fuzzy middle
   that invites a guess.

## What V1 DELIBERATELY DOES NOT do

These are guardrails, not missing features. Each one is a place the promise could break.

- **No math or calculations.** No ratios, growth rates, margins, multiples, P/E.
  Accuracy collapses once calculations chain together; that is the failure that
  kills the brand. Asked to calculate, it returns the raw figures and declines the math.
- **No paraphrasing of numbers — ever.** Every figure is the exact substring from
  the source. Restating a number in the model's words is precisely where a digit flips.
- **No cross-document comparison** in V1 (e.g. 10-Q vs. investor deck). One document at a time.
- **No live or market data.** No current price, market cap, today's P/E. It knows
  only the static document in front of it. (This also keeps it from rotting.)
- **No opinions, predictions, valuations, or buy/sell signals.** It locates facts;
  it is not an analyst.
- **No whole-filing "summarize into takeaways."** It answers asked questions with
  citations; it won't synthesize conclusions it can't pin to a line.

---

## How the promise is enforced (the mechanism)

Two layers, in order:

1. **Retrieve & judge** — find the passage(s) most relevant to the question;
   an entailment judge (LLM or NLI, pluggable — VeriTrace's `LlmJudgeBackend`)
   decides whether the passage actually answers the question. No support → refuse.
2. **Number Guard (the hard gate)** — before any answer leaves the system, every
   number it contains is checked for a **verbatim match** in the cited source text.
   Any figure not found exactly in the source → the answer is refused, not shown.
   This is deterministic, runs with no model, and is the core safety net.

The model proposes; the Number Guard disposes. A figure the model can't tie to an
exact source substring never reaches the user.

---

## Architecture

```
filing (text/PDF)
   -> loader: split into passages (sentence/section level)
   -> retrieve: most relevant passages to the question
   -> judge: does a passage answer it?  (VeriTrace LlmJudgeBackend / NliBackend)
        no  -> "Not stated in this filing."
        yes -> draft answer + candidate citation
   -> Number Guard: every figure verbatim in the cited source?
        no  -> refuse
        yes -> return answer + verbatim quote + location
```

Built directly on the existing **VeriTrace** engine (verification, tiering,
citations, refusal). FilingProof adds: a filing loader, a finance-tuned judge
prompt, and the Number Guard.

## Data

- **SEC EDGAR** is the source of filings — free, stable, government-run, so no
  data-rot risk. V1 takes a user-provided document; fetch-by-ticker from EDGAR is
  a fast, safe follow-up (see Deferred).

## Honest limits (stated on the page — owning them builds the trust)

- It is only as good as the document you give it; it knows nothing beyond that filing.
- It finds and quotes; it does **not** reason or calculate. For analysis you still
  need a person or a paid tool.
- Numbers inside PDF tables are genuinely hard to extract cleanly; where unsure,
  it flags rather than guesses.
- It errs hard toward refusing. Over-refusing is mildly annoying; fabricating once
  is fatal — so when in doubt, it says it can't confirm from the filing.

## Deferred (named, so scope creep stays out of V1)

- EDGAR fetch-by-ticker (easy, safe — next up)
- Multi-filing reconciliation
- Any calculations / financial reasoning
- Live market data

---

## Build split (you + me + a developer where needed)

- **Engine & logic (me):** the loader, the Number Guard, the refusal pipeline,
  tests — built and proven on text in the dev environment.
- **The judge (you):** plug in your LLM key (or a local NLI model) and run it
  against real filings — this needs a live call I can't make here.
- **Hard edges (a developer, when we reach them):** robust PDF/table extraction
  from messy 10-Ks is the genuinely hard part; we scope V1 to text we can nail and
  bring in help for the rest.
