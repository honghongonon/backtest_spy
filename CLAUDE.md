# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page Streamlit app (`app.py`) that simulates future asset growth for ETF holdings (e.g. SPY, QQQ, SCHD) in KRW, based on user-specified annual price growth and dividend yield assumptions. All UI text, labels, and comments are in Korean. There is no backtesting against real historical price data — "assumptions" are hardcoded estimates the user can override.

## Commands

```bash
pip install -r requirements.txt   # streamlit, pandas, numpy, plotly
python -m streamlit run app.py    # run the app locally (also: run.bat on Windows)
```

There are no tests, linter, or build step configured in this repo.

## Architecture

Everything lives in `app.py`, organized as three Streamlit tabs sharing two simulation functions:

- **`simulate(...)`** — single-portfolio simulation used by tab 1 (단일 시나리오) and tab 2 (종목 비교). Tracks three stacked layers over time: 투입한 자산 (contributed principal), 가격 상승분 (capital gains), 배당으로 늘어난 자산 (accumulated dividends). Dividends are applied quarterly (`m % 3 == 0`) at `yield / 4` of the current principal pool, then either reinvested into the same asset, reinvested into a different asset (`other_total_growth`), or held as non-growing cash, per `DIVIDEND_OPTIONS`.
- **`simulate_breakdown(...)`** — per-holding variant used by tab 3 (내 자산 구성), which supports multiple simultaneous holdings with a shared monthly contribution split by current weight. Dividend cash is tracked separately (`배당현금`) so it can optionally be pooled across holdings into one destination asset rather than reinvested per-holding.

Tab 3 also persists user input (holdings table, years, monthly contribution, dividend handling, pool destination) to `saved_portfolio.json` next to `app.py` via `load_saved_state()` / `save_state()`, so the form repopulates on next run. This file is gitignored.

Monthly growth rates are derived from annual inputs via `(1 + annual_rate) ** (1/12) - 1`. Chart styling (colors, fonts, axis formatting) is centralized in `styled_layout()` and the `LAYER_COLORS` / `PORTFOLIO_COLORS` constants — reuse these rather than styling new `go.Figure` traces ad hoc.
