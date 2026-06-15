# FilingProof

**A fact-checker for financial filings that won't make up a number.**

Ask a question about a filing you give it (a 10-K, 10-Q, earnings transcript, or prospectus). FilingProof answers **only** from that document, quotes the exact line, and says **"Not stated in this filing"** instead of guessing. Every figure it reports is verified verbatim against the source before you ever see it — and if the AI slips, the guard catches it.

It's The I Don't Know Project, pointed at finance. Built on the [VeriTrace](https://github.com/waelalebrahim/wa-VeriTrace-project) engine. Free and open source.

## The one promise

> **It will not make up a number.**

The whole design exists to keep that single promise. In finance, a tool that fabricates one figure is finished — so FilingProof refuses rather than risk a wrong number.

## How it works

```
filing -> retrieve relevant lines -> responder drafts an answer from them (or declines)
       -> Number Guard: is every figure verbatim in the cited line?  no -> REFUSE
       -> Answer + verbatim quote + location
```

The **Number Guard** is the safety net. It is deterministic — no model, no API. Before any answer is shown, every financial figure in it must appear *standalone-verbatim* in the cited source. It defeats fabrication, unit conversion (383,285 million → 383.285 billion), rounding (14.7% → 15%), and truncation (383,285 → 383). If a figure can't be tied to the source, the answer is refused. The model proposes; the guard disposes.

## Quickstart

```python
from filingproof import FilingChecker, AnthropicResponder

fc = FilingChecker(AnthropicResponder())   # set ANTHROPIC_API_KEY
fc.load(open("apple_10k.txt").read())

print(fc.ask("What were total net sales in fiscal 2023?"))
# -> answer + the verbatim source line, or "Not stated in this filing."
```

For tests or a custom judge, plug in your own responder:

```python
from filingproof import FilingChecker, FunctionResponder
fc = FilingChecker(FunctionResponder(lambda q, passages: ...))
```

## Install

```bash
# FilingProof builds on VeriTrace. Until both are on PyPI, install VeriTrace first:
pip install -e path/to/wa-VeriTrace-project
pip install -e .
pytest
```

## What it does NOT do (on purpose)

These guardrails are what keep the promise. See `SPEC.md` for the full contract.

- **No math or calculations** — no ratios, growth rates, margins, P/E. That's where accuracy collapses.
- **No paraphrasing numbers** — figures are quoted exactly, never restated.
- **No cross-document comparison** in V1 — one filing at a time.
- **No live/market data** — it knows only the document in front of it.
- **No opinions, predictions, or buy/sell signals** — it locates facts; it is not an analyst.

## Honest limits

- It's only as good as the document you give it.
- It finds and quotes; it does not reason or calculate.
- The guard protects *material* figures (currency, percentages, decimals, thousands, scale words). A bare incidental integer ("3 segments") is treated as prose, not guarded.
- V1 works on clean text. Robust number extraction from messy 10-K **PDFs** is the genuinely hard part and is deferred.

## Roadmap

- [ ] EDGAR fetch-by-ticker (free, stable data — next up)
- [ ] PDF/table extraction for real 10-Ks
- [ ] Multi-filing reconciliation
- [ ] A live web demo (Cloudflare Pages)

## License

MIT. Free to use, copy, modify, and redistribute, with the copyright and author notice preserved.

Created by **Wael Alebrahim**.
