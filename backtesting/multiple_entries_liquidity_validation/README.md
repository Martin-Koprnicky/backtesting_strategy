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

Requires parquet data files for the configured years with 1H, 15M, 5M, and 1S timeframes, loaded via `data.data_handlers.get_data`.

Results are printed as a PrettyTable with per-year stats: ending balance, fees, executed/unexecuted/unfinished zone counts, win rate, average win/loss, and highest win/loss.
