"""
Trade Plotter
=============

Renders candlestick charts with zone overlays, entry levels, and exit markers.
Reads zone data from zones.db and candle data from parquet files.

Two chart types per zone:
1. Overview — full zone lifecycle (zone creation → position close) on the main timeframe
2. Detail   — zoomed in (validation → position close) on one timeframe lower

Usage:
------
    from visualizations.trade_plotter import TradePlotter

    plotter = TradePlotter(config)
    plotter.plot_overview(candles_df, zone_record, output_path)
    plotter.plot_detail(candles_df, zone_record, output_path)
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving PNGs

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PlotConfig:
    """
    Configuration values needed for computing entry levels, SL, and TP on charts.

    These come from the trading config (default_config.toml) but are passed
    explicitly so the plotter doesn't depend on the full Config class.
    """
    entry_levels: List[float]
    stop_loss_percentage: float
    tp_strategy: str
    fixed_tp_multiplier: float


class TradePlotter:
    """
    Renders candlestick charts for individual trades.

    Takes a pandas DataFrame of candles and a ZoneRecord, then draws:
    - Candlestick chart (green/red bodies, black wicks)
    - Zone rectangle (green for demand, red for supply)
    - Entry level lines (dashed gray)
    - Average entry price line (solid blue)
    - Stop loss line (dashed red)
    - Take profit line (dashed green) — only for "fixed" TP strategy
    - Exit marker (different shapes per exit reason)
    """

    def __init__(self, plot_config: PlotConfig):
        self._config = plot_config

    def plot_overview(
        self,
        candles: pd.DataFrame,
        zone,
        output_path: str
    ) -> None:
        """
        Plot the full zone lifecycle: creation → LQ validation → position close.

        Args:
            candles: DataFrame with open_time, open, high, low, close columns
            zone: ZoneRecord from DatabaseReader
            output_path: Where to save the PNG
        """
        fig, ax = plt.subplots(1, 1, figsize=(20, 10))

        self._draw_candlesticks(ax, candles)
        self._draw_zone_rectangle(ax, candles, zone)
        self._draw_entry_levels(ax, candles, zone)
        self._draw_avg_entry_line(ax, candles, zone)
        self._draw_sl_tp_lines(ax, candles, zone)
        self._draw_exit_marker(ax, candles, zone)
        self._draw_validation_marker(ax, candles, zone)
        self._draw_zone_creation_markers(ax, candles, zone)

        # Y-axis: price range with padding
        min_price = candles['low'].min()
        max_price = candles['high'].max()
        price_range = max_price - min_price
        ax.set_ylim(min_price - price_range * 0.02, max_price + price_range * 0.02)

        # X-axis: date labels
        self._set_x_labels(ax, candles)

        # Title
        pnl_str = f"${zone.total_pnl:+.2f}" if zone.total_pnl is not None else "N/A"
        exit_str = zone.exit_reason or "unknown"
        ax.set_title(
            f"{zone.zone_id}  |  {zone.pattern_type.upper()} {zone.zone_type.upper()}  |  "
            f"PnL: {pnl_str}  |  Exit: {exit_str}  |  Entries: {zone.entered_count}",
            fontsize=13, fontweight='bold'
        )
        ax.set_ylabel('Price (USDT)')

        # Legend
        self._add_legend(ax)

        plt.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    def plot_detail(
        self,
        candles: pd.DataFrame,
        zone,
        output_path: str
    ) -> None:
        """
        Plot zoomed detail: validation → position close on a lower timeframe.

        Args:
            candles: DataFrame with lower-timeframe candle data
            zone: ZoneRecord from DatabaseReader
            output_path: Where to save the PNG
        """
        fig, ax = plt.subplots(1, 1, figsize=(20, 10))

        self._draw_candlesticks(ax, candles)
        self._draw_zone_rectangle(ax, candles, zone)
        self._draw_entry_levels(ax, candles, zone)
        self._draw_avg_entry_line(ax, candles, zone)
        self._draw_sl_tp_lines(ax, candles, zone)
        self._draw_exit_marker(ax, candles, zone)

        # Y-axis: price range with padding
        min_price = candles['low'].min()
        max_price = candles['high'].max()
        price_range = max_price - min_price
        ax.set_ylim(min_price - price_range * 0.02, max_price + price_range * 0.02)

        # X-axis: date labels (more granular for lower timeframe)
        self._set_x_labels(ax, candles, fmt='%m-%d %H:%M')

        # Title
        pnl_str = f"${zone.total_pnl:+.2f}" if zone.total_pnl is not None else "N/A"
        exit_str = zone.exit_reason or "unknown"
        ax.set_title(
            f"DETAIL  |  {zone.zone_id}  |  {zone.pattern_type.upper()} {zone.zone_type.upper()}  |  "
            f"PnL: {pnl_str}  |  Exit: {exit_str}",
            fontsize=13, fontweight='bold'
        )
        ax.set_ylabel('Price (USDT)')

        self._add_legend(ax)

        plt.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    # =========================================================================
    # DRAWING HELPERS
    # =========================================================================

    def _draw_candlesticks(self, ax, candles: pd.DataFrame) -> None:
        """Draw candlestick bodies and wicks."""
        for i, (_, row) in enumerate(candles.iterrows()):
            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'

            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])

            # Body
            ax.add_patch(plt.Rectangle(
                (i, body_bottom), 0.8, body_height,
                color=color, zorder=2
            ))

            # Wick
            ax.plot(
                [i + 0.4, i + 0.4], [row['low'], row['high']],
                color='black', linewidth=0.8, zorder=1
            )

    def _draw_zone_rectangle(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw the zone as a semi-transparent rectangle spanning the visible area."""
        zone_color = '#4caf50' if zone.zone_type == 'demand' else '#f44336'

        # Zone spans from first candle to last candle
        width = len(candles)
        rect = plt.Rectangle(
            (0, zone.base_low), width, zone.base_high - zone.base_low,
            facecolor=zone_color, alpha=0.15,
            edgecolor=zone_color, linewidth=1.5,
            linestyle='-', zorder=0
        )
        ax.add_patch(rect)

    def _draw_entry_levels(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw dashed horizontal lines at each entry level within the zone."""
        zone_range = zone.base_high - zone.base_low
        width = len(candles)

        for level in self._config.entry_levels:
            if zone.zone_type == 'demand':
                price = zone.base_low + (level * zone_range)
            else:
                price = zone.base_high - (level * zone_range)

            ax.plot(
                [0, width], [price, price],
                color='gray', linestyle='--', linewidth=0.8, alpha=0.6, zorder=3
            )
            ax.text(
                width + 0.5, price, f"{level}",
                fontsize=8, verticalalignment='center', color='gray',
                zorder=3
            )

    def _draw_avg_entry_line(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw a solid blue line at the average entry price."""
        if zone.average_entry_price is None:
            return

        width = len(candles)
        ax.plot(
            [0, width], [zone.average_entry_price, zone.average_entry_price],
            color='#2196f3', linestyle='-', linewidth=1.5, alpha=0.8, zorder=4
        )
        ax.text(
            width + 0.5, zone.average_entry_price,
            f"avg entry {zone.average_entry_price:.1f}",
            fontsize=8, verticalalignment='center', color='#2196f3',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8),
            zorder=4
        )

    def _draw_sl_tp_lines(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw stop loss (red dashed) and take profit (green dashed) lines."""
        zone_range = zone.base_high - zone.base_low
        width = len(candles)

        # Stop loss
        sl_pct = self._config.stop_loss_percentage
        if zone.zone_type == 'demand':
            sl_price = zone.base_low - (zone_range * sl_pct)
        else:
            sl_price = zone.base_high + (zone_range * sl_pct)

        ax.plot(
            [0, width], [sl_price, sl_price],
            color='#f44336', linestyle='--', linewidth=1.2, alpha=0.7, zorder=3
        )
        ax.text(
            width + 0.5, sl_price, f"SL {sl_price:.1f}",
            fontsize=8, verticalalignment='center', color='#f44336',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8),
            zorder=3
        )

        # Take profit (only for "fixed" strategy, since others are dynamic)
        if self._config.tp_strategy == 'fixed' and zone.average_entry_price is not None:
            if zone.zone_type == 'demand':
                tp_price = zone.average_entry_price + (zone_range * self._config.fixed_tp_multiplier)
            else:
                tp_price = zone.average_entry_price - (zone_range * self._config.fixed_tp_multiplier)

            ax.plot(
                [0, width], [tp_price, tp_price],
                color='#4caf50', linestyle='--', linewidth=1.2, alpha=0.7, zorder=3
            )
            ax.text(
                width + 0.5, tp_price, f"TP {tp_price:.1f}",
                fontsize=8, verticalalignment='center', color='#4caf50',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8),
                zorder=3
            )

    def _draw_exit_marker(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw a marker at the exit point."""
        if zone.exit_price is None or zone.exit_timestamp is None:
            return

        # Find the candle index closest to exit_timestamp
        x_pos = self._timestamp_to_index(candles, zone.exit_timestamp)
        if x_pos is None:
            return

        # Marker style based on exit reason
        markers = {
            'take_profit': ('^', '#ffd700', 120, 'Take Profit'),
            'stop_loss': ('X', '#f44336', 120, 'Stop Loss'),
            '1R_decline': ('v', '#2196f3', 120, '1R Decline'),
        }
        marker, color, size, label = markers.get(
            zone.exit_reason, ('s', '#9c27b0', 100, zone.exit_reason or 'Exit')
        )

        ax.scatter(
            x_pos, zone.exit_price, color=color,
            marker=marker, s=size, zorder=6,
            edgecolor='white', linewidth=1.5
        )

        # Label above/below the marker
        zone_range = zone.base_high - zone.base_low
        offset = zone_range * 0.3
        if zone.zone_type == 'demand':
            text_y = zone.exit_price + offset
        else:
            text_y = zone.exit_price - offset

        ax.text(
            x_pos, text_y, f"{label}\n{zone.exit_price:.1f}",
            fontsize=9, ha='center', color=color, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9),
            zorder=7
        )

    def _draw_validation_marker(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw a vertical dashed line at zone validation time (overview only)."""
        if zone.validated_at is None:
            return

        x_pos = self._timestamp_to_index(candles, zone.validated_at)
        if x_pos is None:
            return

        ax.axvline(
            x=x_pos, color='#ff9800', linestyle=':', linewidth=1.2, alpha=0.6, zorder=3
        )
        ax.text(
            x_pos + 0.5, ax.get_ylim()[1],
            'validated', fontsize=8, color='#ff9800',
            verticalalignment='top', rotation=90, alpha=0.7,
            zorder=3
        )

    def _draw_zone_creation_markers(self, ax, candles: pd.DataFrame, zone) -> None:
        """Draw vertical lines at zone creation and first base candle."""
        from datetime import timedelta

        # created_at marker (when zone pattern was fully detected, after move_after)
        x_created = self._timestamp_to_index(candles, zone.created_at)
        if x_created is not None:
            ax.axvline(
                x=x_created, color='#9c27b0', linestyle='--', linewidth=1.5, alpha=0.7, zorder=3
            )
            ax.text(
                x_created + 0.5, ax.get_ylim()[1],
                'created', fontsize=8, color='#9c27b0',
                verticalalignment='top', rotation=90, alpha=0.8,
                zorder=3
            )

        # First base candle marker
        # created_at is after move_after, so first base candle is
        # (move_after_candles + base_candle_count - 1) candles back
        candles_back = zone.move_after_candles + zone.base_candle_count - 1
        first_base_time = zone.created_at - timedelta(hours=candles_back)
        x_first_base = self._timestamp_to_index(candles, first_base_time)
        if x_first_base is not None:
            ax.axvline(
                x=x_first_base, color='#00bcd4', linestyle='--', linewidth=1.5, alpha=0.7, zorder=3
            )
            ax.text(
                x_first_base + 0.5, ax.get_ylim()[1],
                'base[0]', fontsize=8, color='#00bcd4',
                verticalalignment='top', rotation=90, alpha=0.8,
                zorder=3
            )

    # =========================================================================
    # UTILITY HELPERS
    # =========================================================================

    def _timestamp_to_index(self, candles: pd.DataFrame, timestamp) -> Optional[int]:
        """
        Find the candle index closest to a given timestamp.

        Returns None if the timestamp is outside the candle range.
        """
        times = candles['open_time']

        # Exact match
        exact = times[times == timestamp]
        if not exact.empty:
            return exact.index[0] - times.index[0]

        # Closest match (find the last candle at or before the timestamp)
        before = times[times <= timestamp]
        if not before.empty:
            idx = before.index[-1]
            return idx - times.index[0]

        # Timestamp is before all candles
        return None

    def _set_x_labels(self, ax, candles: pd.DataFrame, fmt: str = '%Y-%m-%d') -> None:
        """Set readable date labels on the x-axis."""
        n = len(candles)
        step = max(1, n // 12)
        ticks = list(range(0, n, step))
        labels = [candles.iloc[i]['open_time'].strftime(fmt) for i in ticks]

        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)

    def plot_measurement(
        self,
        candles: pd.DataFrame,
        zone_high: float,
        zone_low: float,
        zone_type: str,
        title: str,
        output_path: str
    ) -> None:
        """
        Plot a simple candlestick chart with only the zone rectangle.
        Used by Measurements to visualize price action around entry.
        """
        fig, ax = plt.subplots(1, 1, figsize=(20, 10))

        self._draw_candlesticks(ax, candles)

        # Zone rectangle
        zone_color = '#4caf50' if zone_type == 'demand' else '#f44336'
        width = len(candles)
        rect = plt.Rectangle(
            (0, zone_low), width, zone_high - zone_low,
            facecolor=zone_color, alpha=0.15,
            edgecolor=zone_color, linewidth=1.5,
            linestyle='-', zorder=0
        )
        ax.add_patch(rect)

        # Y-axis
        min_price = candles['low'].min()
        max_price = candles['high'].max()
        price_range = max_price - min_price
        ax.set_ylim(min_price - price_range * 0.02, max_price + price_range * 0.02)

        # X-axis
        self._set_x_labels(ax, candles, fmt='%m-%d %H:%M')

        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.set_ylabel('Price (USDT)')

        plt.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

    def _add_legend(self, ax) -> None:
        """Add a legend explaining the chart elements."""
        elements = [
            mpatches.Patch(facecolor='#4caf50', alpha=0.15, edgecolor='#4caf50', label='Demand Zone'),
            mpatches.Patch(facecolor='#f44336', alpha=0.15, edgecolor='#f44336', label='Supply Zone'),
            plt.Line2D([0], [0], color='#2196f3', linewidth=1.5, label='Avg Entry'),
            plt.Line2D([0], [0], color='gray', linestyle='--', linewidth=0.8, label='Entry Levels'),
            plt.Line2D([0], [0], color='#f44336', linestyle='--', linewidth=1.2, label='Stop Loss'),
            plt.Line2D([0], [0], color='#4caf50', linestyle='--', linewidth=1.2, label='Take Profit'),
            plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#ffd700', markersize=8, label='TP Exit'),
            plt.Line2D([0], [0], marker='X', color='w', markerfacecolor='#f44336', markersize=8, label='SL Exit'),
            plt.Line2D([0], [0], marker='v', color='w', markerfacecolor='#2196f3', markersize=8, label='1R Exit'),
        ]
        ax.legend(handles=elements, loc='upper left', fontsize=8, framealpha=0.9)
