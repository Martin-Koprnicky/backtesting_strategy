# Multiple Entries Liquidity Validation Backtester

Backtesting engine for a supply/demand zone trading strategy on cryptocurrency data. The strategy detects price consolidation zones (bases), validates them through liquidity retracements, and executes positions with multiple scaled entry levels. It runs on historical 1H/5M/1S data from 2018 to 2025.

## Strategy Overview

The core idea: find areas where price consolidated (the "base"), confirm that price left the base with strength, wait for a liquidity-validated retracement, and then trade the re-entry into the zone with multiple limit orders at different price levels.

**Zone types:** Demand (bullish) and Supply (bearish)

**Six patterns detected:**
- **BR / BD** — Base-Rally and Base-Drop (two-leg patterns)
- **RBR / RBD** — Rally-Base-Rally and Rally-Base-Drop (three-leg patterns)
- **DBR / DBD** — Drop-Base-Rally and Drop-Base-Drop (three-leg patterns)

## Detection Pipeline

The detection runs on 1H candles and follows four stages:

### 1. Base Detection
Scans for consecutive candles that stay within a configurable price range (`base.max_range`). For each starting candle, all valid base lengths (from `min` to `max` candle count) are generated as candidates. This intentional over-generation ensures no strong zone is missed due to an off-by-one base boundary — duplicates are cleaned up in step 4.

### 2. Strong Movement Validation
Two independent checks — movement **before** and movement **after** the base:

- **Direction** — all candles must move in the expected direction (e.g. rally after a demand base)
- **Progressive movement** — each candle should extend further than the previous one (configurable, typically required for movement-after only)
- **Candle range & body strength** — candles must have a minimum body-to-range ratio and pass a strength score threshold

Movement-after is stricter (requires strong departure from the base). Movement-before is more lenient (only cares about range, not individual candle strength).

### 3. Liquidity Validation
After a zone is detected, price must complete a three-phase retracement pattern before the zone becomes tradeable:

1. **Looking phase** — track the highest high (demand) or lowest low (supply) after the base
2. **Retracement phase** — price must pull back 70-95% of the move (configurable) without touching the base
3. **Breakout phase** — price must reclaim the previous extreme, confirming the liquidity sweep

This filters out zones that never get a clean re-entry opportunity. Times out after `timeout_hours` (default 70h).

### 4. Overlap Removal
Zones whose base indices are within 5 hours of each other are deduplicated, keeping the best candidate.

## Trade Execution

Once a zone is validated, the execution engine takes over:

1. **Scan (1H)** — checks if price re-enters the zone within `entry_timeout_hours` (default 100h)
2. **Narrow down (5M)** — finds the exact 5-minute candle of entry to minimize the 1-second data window
3. **Execute (1S)** — triggers entry levels one by one as price moves through the zone, tracks SL/TP tick-by-tick

**Multiple entries:** Positions use scaled entry levels (default: 100%, 80%, 60%, 40% of the zone range), each risking a fixed dollar amount (`entry_risk`). Deeper entries get more coins for the same dollar risk, improving the average entry price.

**Exit logic:**
- **Take profit** — fixed multiplier (default 2.2R) above/below the zone
- **Stop loss** — placed beyond the zone edge with a small buffer (`stop_loss_moved`)
- Fee validation ensures the zone's spread is wide enough that maker fees don't eat the edge

## Project Structure

```
multiple_entries_liquidity_validation/
    run.py                  # Entry point — loops through years, orchestrates detection + execution
    pattern_detection.py    # PatternDetector — base finding, movement validation, liquidity validation
    trade_execution.py      # BacktestEngine — scanning, entry triggering, SL/TP tracking, P&L
    dataclasses.py          # All data models (Zone, Base, Position, Entry, etc.)
    config/
        default_config.toml # All tunable parameters
        log_config.py       # Config loader (TOML -> typed dataclasses)
    visualizations/
        visualizer.py       # Adapts Zone objects to the plotter interface
        trade_plotter.py    # Candlestick chart renderer with zone overlays
    zones.csv               # Output — all executed zones with pattern type and P&L
    capital_growth.png      # Output — equity curve chart
```

## Configuration

All parameters live in `config/default_config.toml`. Key sections:

| Section | What it controls |
|---|---|
| `[general]` | Which patterns to detect, which years to backtest |
| `[base]` | Max price range, candle count limits |
| `[movement_before]` / `[movement_after]` | Candle count, range, strength thresholds |
| `[liquidity_validation]` | Retracement depth, timeout, wick rules |
| `[trading]` | Entry levels, timeouts, stop loss buffer |
| `[risk]` | Starting capital, per-zone and per-entry risk |
| `[fees]` | Maker/taker fee rates, fee threshold |

## Usage

```python
python -m backtesting.multiple_entries_liquidity_validation.run
```

## Sample Results

Results from backtesting on BTC historical data (2018–2025), starting capital $1000 per year. This is a research tool, not financial advice.

Patterns: DBD, DBR, RBD, RBR

| Year | End. balance | Fees | E. zones | Unexe. zones | Unfin. zones | Entries hit | Avg entry hit | Win rate | Loss rate | Avg win | Avg loss | H. win | H. loss |
|------|-------------|-------|----------|--------------|--------------|-------------|---------------|----------|-----------|---------|----------|--------|---------|
| 2018 | 1171.67 | 61.28 | 88 | 0 | 0 | 270 | 3.07 | 57.95 | 42.05 | 11.97 | -11.85 | 41.2 | -14.84 |
| 2019 | 1295.49 | 48.91 | 64 | 0 | 0 | 184 | 2.88 | 67.19 | 32.81 | 12.48 | -11.49 | 41.03 | -14.47 |
| 2020 | 1175.14 | 85.81 | 80 | 0 | 0 | 251 | 3.14 | 62.5 | 37.5 | 10.68 | -11.97 | 40.85 | -14.81 |
| 2021 | 1093.54 | 80.71 | 104 | 0 | 0 | 327 | 3.14 | 57.69 | 42.31 | 10.06 | -11.6 | 40.9 | -13.41 |
| 2022 | 974.23 | 95.68 | 93 | 0 | 0 | 296 | 3.18 | 58.06 | 41.94 | 8.35 | -12.22 | 40.73 | -14.83 |
| 2023 | 1182.93 | 85.83 | 55 | 0 | 0 | 182 | 3.31 | 61.82 | 38.18 | 12.54 | -11.59 | 40.83 | -14.89 |
| 2024 | 975.49 | 131.94 | 111 | 0 | 0 | 351 | 3.16 | 52.25 | 47.75 | 10.62 | -12.08 | 40.69 | -14.9 |
| 2025 | 958.49 | 150.27 | 96 | 0 | 0 | 316 | 3.29 | 48.96 | 51.04 | 11.84 | -12.2 | 40.81 | -14.92 |
| **AVG** | **1103.37** | **92.55** | **86.38** | **0.0** | **0.0** | **272.12** | **3.15** | **58.3** | **41.7** | **11.07** | **-11.88** | **40.88** | **-14.63** |

Requires parquet data files for the configured years with 1H, 15M, 5M, and 1S timeframes. Data are not accessable, due to exceeding memory size of 10GB.
