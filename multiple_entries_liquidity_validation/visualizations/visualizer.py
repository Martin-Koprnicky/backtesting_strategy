"""
Backtesting Visualizer
======================

Adapts backtesting Zone objects to the TradePlotter interface and generates
overview + detail PNG charts for every executed zone.

Usage:
------
    from backtesting.multiple_entries_liquidity_validation.visualizer import BacktestVisualizer

    visualizer = BacktestVisualizer(config, data)
    visualizer.plot_all(executed_zones, output_dir="backtesting/multiple_entries_liquidity_validation/output/charts")
"""

import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backtesting.multiple_entries_liquidity_validation.config.log_config import Config
from backtesting.multiple_entries_liquidity_validation.pattern_detection import Zone
from backtesting.multiple_entries_liquidity_validation.visualizations.trade_plotter import TradePlotter, PlotConfig


@dataclass
class ZoneRecord:
    """
    Flat representation of a completed backtesting trade.

    Mirrors the shape that TradePlotter expects, built from a backtesting Zone.
    """
    zone_id:               str
    pattern_type:          str            # e.g. "RBR"
    zone_type:             str            # "demand" | "supply"
    base_low:              float
    base_high:             float
    average_entry_price:   Optional[float]
    exit_price:            Optional[float]
    exit_reason:           Optional[str]  # "take_profit" | "stop_loss"
    exit_timestamp:        Optional[pd.Timestamp]
    total_pnl:             Optional[float]
    validated_at:          Optional[pd.Timestamp]
    created_at:            Optional[pd.Timestamp]
    move_after_candles:    int
    base_candle_count:     int
    entered_count:         int

    @classmethod
    def from_zone(cls, zone: Zone, idx: int, data_1h_index) -> "ZoneRecord":
        created_i  = zone.movement_after.start_idx + zone.movement_after.candle_count - 1
        created_at = pd.Timestamp(data_1h_index[created_i]) if created_i < len(data_1h_index) else None
        validated  = pd.Timestamp(zone.lq_validation.validation_time)

        return cls(
            zone_id             = f"{idx:04d}_{validated.strftime('%Y%m%d')}_{zone.pattern.name}_{zone.type.value}",
            pattern_type        = zone.pattern.name,
            zone_type           = zone.type.value,
            base_low            = zone.base.low,
            base_high           = zone.base.high,
            average_entry_price = zone.position.average_entry_price if zone.position.total_coins > 0 else None,
            exit_price          = zone.position.exit_price,
            exit_reason         = zone.position.exit_reason.value if zone.position.exit_reason else None,
            exit_timestamp      = pd.Timestamp(zone.position.exit_timestamp) if zone.position.exit_timestamp else None,
            total_pnl           = zone.stats.netto,
            validated_at        = validated,
            created_at          = created_at,
            move_after_candles  = zone.movement_after.candle_count,
            base_candle_count   = zone.base.candle_count,
            entered_count       = zone.position.executed_entries_count,
        )


class BacktestVisualizer:

    OVERVIEW_PAD = 10   # extra 1h candles on each side of the overview
    DETAIL_PAD   = 20   # extra 5m candles after the exit on the detail

    def __init__(self, config: Config, data: dict):
        self._data_1h = data['1h']
        self._data_5m = data['5m']

        tp_strategy = 'fixed' if config.strategy.fixed_tp else ('mountain' if config.strategy.mountain_tp else None)

        self._plotter = TradePlotter(PlotConfig(
            entry_levels        = config.trading.entry_levels,
            stop_loss_percentage= config.trading.stop_loss_moved,
            tp_strategy         = tp_strategy,
            fixed_tp_multiplier = config.strategy.price_level_tp,
        ))

    def plot_all(self, executed_zones: list[Zone], output_dir: str = "backtesting/multiple_entries_liquidity_validation/output/charts", top_n: int = None, detail: bool = True) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        sorted_by_pnl = sorted(executed_zones, key=lambda z: z.stats.netto, reverse=True)

        if top_n == 'ALL':
            selection = sorted_by_pnl
        elif top_n is None:
            selection = executed_zones
        else:
            selection = sorted_by_pnl[:top_n] + sorted_by_pnl[-top_n:]

        for zone in selection:
            i = executed_zones.index(zone)
            record = ZoneRecord.from_zone(zone, i, self._data_1h.index)
            self._plot_overview(record, out)
            if detail is True:
                self._plot_detail(record, out)

    # ── chart generators ──────────────────────────────────────────────────────

    def _plot_overview(self, record: ZoneRecord, out: Path) -> None:
        candles = self._slice_1h(record)
        if candles is None or len(candles) < 2:
            return
        path = out / f"{record.zone_id}_aoverview.png"
        self._plotter.plot_overview(candles, record, str(path))

    def _plot_detail(self, record: ZoneRecord, out: Path) -> None:
        candles = self._slice_5m(record)
        if candles is None or len(candles) < 2:
            return
        path = out / f"{record.zone_id}_detail.png"
        self._plotter.plot_detail(candles, record, str(path))

    # ── candle window helpers ─────────────────────────────────────────────────

    def _slice_1h(self, record: ZoneRecord) -> Optional[pd.DataFrame]:
        if record.exit_timestamp is None:
            return None

        anchor = record.created_at or record.validated_at
        if anchor is None:
            return None

        idx = self._data_1h.index
        start_i = max(0, idx.searchsorted(anchor, side='left') - self.OVERVIEW_PAD)
        end_i   = min(len(idx) - 1, idx.searchsorted(record.exit_timestamp, side='right') + self.OVERVIEW_PAD)

        return self._to_candles_df(self._data_1h.iloc[start_i : end_i + 1])

    def _slice_5m(self, record: ZoneRecord) -> Optional[pd.DataFrame]:
        if record.validated_at is None or record.exit_timestamp is None:
            return None

        end_ts = record.exit_timestamp + pd.Timedelta(minutes=5 * self.DETAIL_PAD)
        idx = self._data_5m.index
        start_i = idx.searchsorted(record.validated_at, side='left')
        end_i   = min(len(idx) - 1, idx.searchsorted(end_ts, side='right'))
        return self._to_candles_df(self._data_5m.iloc[start_i : end_i + 1])

    @staticmethod
    def _to_candles_df(df: pd.DataFrame) -> pd.DataFrame:
        """Reset the datetime index to an `open_time` column (required by TradePlotter)."""
        out = df.copy()
        out.index.name = 'open_time'
        return out.reset_index()
