"""
Trade Execution
===============

Executes validated supply/demand zones: checks if price re-enters,
validates fees, creates positions, and tracks P&L.

Trading Flow
------------
1. Scan (1H timeframe)
    Checks if price re-enters the zone within the entry timeout.
    If hit, moves to the 5M window for a more precise candle.

2. Narrow down (5M timeframe)
    Finds which 5M candle price enters the zone on, to avoid iterating
    through 3600 S1 candles. Slices a ~300 candle S1 window from there.

3. Execute (S1 timeframe)
    Triggers and executes entry levels, tracks stop loss and take profit
    on every S1 candle until the position ends.

4. Portfolio update
    Calculates brutto, fees, and netto P&L. Updates capital and
    sorts the zone into executed, unexecuted, or unfinished buckets.
"""

import pandas as pd
import numpy as np

from typing import Optional
from copy import copy

from backtesting.multiple_entries_liquidity_validation.config.log_config import Config
from backtesting.multiple_entries_liquidity_validation.pattern_detection import Zone
from backtesting.multiple_entries_liquidity_validation.dataclasses import (
    Entry, Position, ExitReason, TradeStatistics
)
from data.numpy import numpy_arrays


class FeeValidator:
    """Validates whether a zone's entry fee is acceptable relative to zone risk."""

    def __init__(self, config: Config):
        """
        Initialize the fee validator.

        Args:
            config : Full strategy configuration
        """
        self.config = config

    def maker_fee(self, price: float, amount: float) -> float:
        return price * amount * self.config.fees.maker_fee
    
    def taker_fee(self, price: float, amount: float) -> float:
        return price * amount * self.config.fees.taker_fee
    
    def fee_validation(self, zone: Zone) -> bool:
        """Validate if zone's fee are acceptable for tading."""

        if zone.base_range == 0:
            return False
        
        coin_amount = self.config.risk.zone_risk / zone.base_range
        fee = self.maker_fee(zone.base.high if zone.is_demand else zone.base.low, coin_amount)

        if fee > (self.config.fees.entry_threshold * self.config.risk.zone_risk):
            return False
        
        return True
    
class DataWindow:
    """Holds multi-timeframe data and provides windowed slices for trade scanning and execution."""

    def __init__(self, data: dict[pd.DataFrame], config: Config):
        """
        Initialize the data window.

        Args:
            data : Dict of DataFrames keyed by timeframe ('1h', '15m', '5m', '1s')
            config : Full strategy configuration
        """
        self.data = data
        self.data_1h = self.data['1h']
        self.data_15m = self.data['15m']
        self.data_5m = self.data['5m']
        self.data_1s = self.data['1s']

        self.config = config

    def get_5m_window(self, start_idx: int, end_idx: int) -> pd.DataFrame:
        """Returns data window on 5m timeframe."""

        return numpy_arrays(self.data_5m.loc[start_idx:end_idx])

    def scan_execution(self, zone: Zone) -> None:
        """Scan of data, if price hit the zone."""

        start_time = zone.lq_validation.validation_time + pd.Timedelta(hours = 1)
        end_time = start_time + pd.Timedelta(hours=self.config.trading.entry_timeout_hours)
        window = self.data_1h.loc[start_time:end_time]

        h_arrays = numpy_arrays(window)
        h_lows = h_arrays['lows']
        h_highs = h_arrays['highs']
        h_timestamps = h_arrays['timestamps']

        time_before_min = 0

        # Scan through 1h timeframe, in order to find out if the zone as hit in time limit.
        # If yes, continue with 5m one hour window, for quick scan where exactly the enter happens. 
        # Otherwise return None.

        for candle in range(len(h_lows)):
            if (zone.is_demand and h_lows[candle] < zone.starting_entry_price) or (zone.is_supply and h_highs[candle] > zone.starting_entry_price):
                entering_candle = pd.Timestamp(h_timestamps[candle])
                end_time = entering_candle + pd.Timedelta(hours=1)

                zone.scan_window = self.data_5m.loc[entering_candle:end_time]
                zone.time_before_entry = time_before_min
                zone.position.entry_timestamp = entering_candle
                return True
            time_before_min += 60

        return None
        
    def get_trading_window(self, zone: Zone) -> Optional[pd.DataFrame]:
        """Prepare trading window for executing the trade."""

        m_arrays = numpy_arrays(zone.scan_window)
        m_lows = m_arrays['lows']
        m_highs = m_arrays['highs']
        m_timestamps = m_arrays['timestamps']

        time_before_min = 0

        # Scan 5m candles to find exact entry candle, then slice S1 window from there
        for candle in range(len(m_lows)):
            time_before_min += 5
            if (zone.is_demand and m_lows[candle] < zone.starting_entry_price) or (zone.is_supply and m_highs[candle] > zone.starting_entry_price):
                entering_5m_candle = pd.Timestamp(m_timestamps[candle])
                end_time_5m = entering_5m_candle + pd.Timedelta(hours=self.config.trading.exit_timeout_hours)
                window_1s = self.data_1s.loc[entering_5m_candle:end_time_5m]
                break

        zone.time_before_entry += time_before_min

        return window_1s
    
class PositionManager:
    """Creates and executes positions for a single zone, including entries, stop loss, and take profit."""

    def __init__(self, zone: Zone, config: Config, data_window: DataWindow, fee_validator: FeeValidator):
        """
        Initialize the position manager.

        Args:
            zone : Zone to trade
            config : Full strategy configuration
            data_window : DataWindow instance for accessing timeframe slices
            fee_validator : FeeValidator instance for fee checks
        """
        self.zone = zone
        self.config = config
        self.data_window = data_window
        self.fee_validator = fee_validator

    def _get_entries(self, zone: Zone) -> list[Entry]:
        """Calculate all entry levels for a zone."""

        entries = list()
        risk = self.config.risk.entry_risk

        entry_highlight = self.config.trading.entry_level_highlight

        for entry_level in self.config.trading.entry_levels:

            # Calculate price level and coin amount based on zone direction
            if zone.is_demand:
                price_level = (entry_level * zone.base_range) + zone.base.low - (zone.base.price_range if self.config.trading.minus_base_range else 0)
                coin_amount = risk / (price_level - zone.base.low)
            elif zone.is_supply:
                price_level = zone.base.high - (entry_level * zone.base_range) + (zone.base.price_range if self.config.trading.minus_base_range else 0)
                coin_amount = risk / (zone.base.high - price_level)

            dollar_amount = coin_amount * price_level

            entry = Entry(
                level=entry_level,
                price=price_level,
                risk=risk,
                coin_amount=(coin_amount)*2 if entry_level == entry_highlight else coin_amount,
                dollar_amount=(dollar_amount)*2 if entry_level == entry_highlight else dollar_amount,
            )

            entries.append(entry)

        return entries
    
    def _get_stop_loss(self, zone: Zone) -> float:

        # Move stop loss slightly outside the base using config multiplier
        minus_base_range = (zone.base.price_range if self.config.trading.minus_base_range else 0)
        raw_stop_loss = zone.base.low - minus_base_range if zone.is_demand else zone.base.high + minus_base_range
        stop_loss_moved_value = self.config.trading.stop_loss_moved * zone.base_range 
        stop_loss = raw_stop_loss - stop_loss_moved_value if zone.is_demand else raw_stop_loss + stop_loss_moved_value

        return stop_loss
    
    def _get_take_profit_value(self, zone: Zone) -> Optional[float]:

        # Fixed TP: price level calculated from base range and config multiplier
        minus_base_range = (zone.base.price_range if self.config.trading.minus_base_range else 0)
        if self.config.strategy.fixed_tp:

            if zone.is_demand:
                take_profit = zone.base.high + (zone.base_range * self.config.strategy.price_level_tp) - minus_base_range
            elif zone.is_supply:
                take_profit = zone.base.low - (zone.base_range * self.config.strategy.price_level_tp) + minus_base_range

        # Mountain TP: highest high / lowest low from 5m window before entry
        elif self.config.strategy.mountain_tp:

            if zone.is_demand:
                arrays = self.data_window.get_5m_window(zone.lq_validation.validation_time, zone.position.entry_candle)
                take_profit = max(arrays['highs'])
            elif zone.is_supply:
                arrays = self.data_window.get_5m_window(zone.lq_validation.validation_time, zone.position.entry_candle)
                take_profit = min(arrays['lows'])

        else:
            take_profit = None

        return take_profit
    

    def create_position(self, zone: Zone) -> None:

        position = Position(
            entries=self._get_entries(zone),
            stop_loss=self._get_stop_loss(zone),
        )

        zone.position = position

        return
    
    def execute_trade(self, zone: Zone, window_1s: pd.DataFrame) -> Zone:

        if window_1s is None:
            return

        position = zone.position
        position.take_profit = self._get_take_profit_value(zone)

        strategy = self.config.strategy

        arrays = numpy_arrays(window_1s)
        highs = arrays['highs']
        lows = arrays['lows']
        timestamps = arrays['timestamps']

        time_during_trade = 0

        for candle in range(len(lows)):
            candle_low, candle_high, candle_timestamp = lows[candle], highs[candle], timestamps[candle]
            time_during_trade += 1

            # Trigger entries when price touches entry level
            for entry in position.entries:
                if not entry.triggered and ((zone.is_demand and candle_low <= entry.price)
                                            or (zone.is_supply and candle_high >= entry.price)):
                    entry.triggered = True

            # Execute triggered entries and update 1R if needed
            for entry in position.entries:
                if entry.triggered and not entry.executed:

                    entry.executed = True
                    entry.execution_time = candle_timestamp

                    self._update_one_r(zone) if self.config.strategy.full_zone_one_r else None

            # Check stop loss and take profit while position is active
            if position.is_active:

                self._update_one_r_thresholds(zone, candle_high, candle_low) if self.config.strategy.full_zone_one_r else None
                self._try_exit_by_stop_loss(zone, candle_high, candle_low)

                if strategy.fixed_tp is True or strategy.mountain_tp is True:
                    self._try_exit_by_fixed_tp(zone, candle_high, candle_low)

            if position.ended:
                zone.position.time_during_trade = time_during_trade
                zone.position.exit_timestamp = candle_timestamp
                return

    def _update_one_r(self, zone: Zone) -> None:
        
        strategy = self.config.strategy
        position = zone.position

        # Full zone 1R: threshold set once from base range, on first entry
        if strategy.full_zone_one_r and position.one_r_threshold is None:
            position.one_r_range = zone.base_range

            if zone.is_demand:
                position.one_r_threshold = zone.base.high + position.one_r_range

            elif zone.is_supply:
                position.one_r_threshold = zone.base.low - position.one_r_range

        # Last entry 1R: threshold recalculated after each new entry
        elif strategy.last_entry_one_r:
            last_executed_entry = self._get_last_executed_entry(zone)
            position.one_r_range = zone.base_range * last_executed_entry.level

            if zone.is_demand:
                position.one_r_threshold = zone.base.low + (position.one_r_range * 2)

            elif zone.is_supply:
                position.one_r_threshold = zone.base.high - (position.one_r_range * 2)

            # Reset values only for last_entry strat
            # For full zone we don't need reset values after each entry
            position.highest_high = 0
            position.lowest_low = float('inf')

        position.one_r_threshold_triggered = False

    def _get_last_executed_entry(self, zone: Zone) -> Entry:

        entries = copy(zone.position.entries)
        exe_entries = list()

        # Filter for executed entries only
        for entry in entries:
            if entry.executed is True:
                exe_entries.append(entry)

        # Return deepest entry in zone (lowest level for demand, highest for supply)
        if zone.is_demand:
            return min(exe_entries, key=lambda entry: entry.level)
        elif zone.is_supply:
            return max(exe_entries, key=lambda entry: entry.level)

    def _update_one_r_thresholds(self, zone: Zone, candle_high: float, candle_low: float) -> None:

        position = zone.position

        # Update thresholds
        if zone.is_demand:
            if candle_high > position.highest_high:
                position.highest_high = candle_high
            if position.highest_high > position.one_r_threshold:
                position.one_r_threshold_triggered = True
                position.stop_loss = position.highest_high - position.one_r_range

        elif zone.is_supply:
            if candle_low < position.lowest_low:
                position.lowest_low = candle_low
            if position.lowest_low < position.one_r_threshold:
                position.one_r_threshold_triggered = True
                position.stop_loss = position.lowest_low + position.one_r_range
        
    def _try_exit_by_stop_loss(self, zone: Zone, candle_high: float, candle_low: float) -> None:

        if zone.is_demand and candle_low < zone.position.stop_loss:
            zone.position.exit_price = zone.position.stop_loss
            zone.position.exit_reason = ExitReason.STOP_LOSS

        elif zone.is_supply and candle_high > zone.position.stop_loss:
            zone.position.exit_price = zone.position.stop_loss
            zone.position.exit_reason = ExitReason.STOP_LOSS

    def _try_exit_by_fixed_tp(self, zone: Zone, candle_high: float, candle_low: float) -> None:

        if zone.is_demand and candle_high > zone.position.take_profit:
            zone.position.exit_price = zone.position.take_profit
            zone.position.exit_reason = ExitReason.TAKE_PROFIT

        elif zone.is_supply and candle_low < zone.position.take_profit:
            zone.position.exit_price = zone.position.take_profit
            zone.position.exit_reason = ExitReason.TAKE_PROFIT

class BacktestEngine:
    """Orchestrates the full backtest: iterates zones, validates fees, executes trades, and records results."""

    def __init__(self, zones: list[Zone], config: Config, data_plus_month: dict[pd.DataFrame]):
        """
        Initialize the backtest engine.

        Args:
            zones : List of validated zones from pattern detection
            config : Full strategy configuration
            data_plus_month : Dict of DataFrames keyed by timeframe ('1h', '15m', '5m', '1s')
        """
        self.zones = zones
        self.config = config
        self.data = data_plus_month

        self.window = DataWindow(self.data, self.config)
        self.fee_validator = FeeValidator(self.config)
        self.portfolio = Portfolio(self.config)

    def run(self):

        for zone in self.zones:

            # Skip if fees are too high relative to zone risk
            if not self.fee_validator.fee_validation(zone):
                continue

            position_manager = PositionManager(zone, self.config, self.window, self.fee_validator)
            position_manager.create_position(zone)

            # Skip if price never re-enters the zone within timeout
            if not self.window.scan_execution(zone):
                continue

            # Create position, get S1 window, execute trade, record result
            window_1s = self.window.get_trading_window(zone)
            position_manager.execute_trade(zone, window_1s)
            self.portfolio.add_trade(zone)

        return self.portfolio.get_summary(), self.portfolio.executed_zones

class Portfolio:
    """Tracks capital, executed zones, and aggregated trade statistics across the backtest."""

    def __init__(self, config: Config):
        """
        Initialize the portfolio.

        Args:
            config : Full strategy configuration
        """
        self.config = config
        self.initial_capital: int = self.config.risk.capital
        self.current_capital: int = self.initial_capital
        self.executed_zones: list[Zone] = []
        self.unexecuted_zones: list[Zone] = []
        self.unfinished_zones: list[Zone] = []
        self.total_fees: int = 0


    @property
    def total_zones(self) -> int:
        return (len(self.executed_zones) + len(self.unexecuted_zones)) if self.executed_zones else 0
    
    @property
    def wins(self) -> list[Zone]:
        return [zone for zone in self.executed_zones if zone.stats.netto > 0]
    
    @property
    def losses(self) -> list[Zone]:
        return [zone for zone in self.executed_zones if zone.stats.netto <= 0]
    
    @property
    def executed_entries_count(self) -> int:
        executed_entries = 0
        for zone in self.executed_zones:
            executed_entries += sum(1 for entry in zone.position.entries if entry.executed)

        return executed_entries

    @property
    def average_executed_entries_count(self) -> float:
        return self.executed_entries_count / len(self.executed_zones)
    
    @property
    def win_rate(self) -> float:
        return len(self.wins) / len(self.executed_zones) * 100 if self.executed_zones else 0.0
    
    @property
    def loss_rate(self) -> float:
        return len(self.losses) / len(self.executed_zones) * 100 if self.executed_zones else 0.0
    
    @property
    def average_win(self) -> float:
        return np.average([zone.stats.netto for zone in self.wins]) if self.wins else 0.0
    
    @property
    def average_loss(self) -> float:
        return np.average([zone.stats.netto for zone in self.losses]) if self.losses else 0.0
    
    @property
    def highest_win(self) -> float:
        return max(zone.stats.netto for zone in self.wins) if self.wins else 0.0
    
    @property
    def highest_loss(self) -> float:
        return min(zone.stats.netto for zone in self.losses) if self.losses else 0.0

    def add_trade(self, zone: Zone) -> None:

        # Route zone to correct bucket based on position state
        if zone.position.is_active is False:
            self.unexecuted_zones.append(zone)
        elif zone.position.is_active and zone.position.exit_price is None:
            self.unfinished_zones.append(zone)
        else:
            # self._do_research(zone) if len(self.executed_zones) == 0
                
            self.executed_zones.append(zone)
            self._update_portfolio(zone)

    def _do_research(self, zone: Zone) -> None:

        avg_price = zone.position.average_entry_price
        entry_fees = zone.position.total_dollars * self.config.fees.maker_fee
        exit_dollar_amount = zone.position.exit_price * zone.position.total_coins

        print(f"average entry price = {avg_price}")
        print(f"zone position total dollar = {zone.position.total_dollars}")
        print(f"entry fees = {zone.position.total_dollars * self.config.fees.maker_fee}")
        print(f"exit dollar amount = {exit_dollar_amount}")
        print(f"exit price = {zone.position.exit_price}")

        if zone.position.exit_reason == ExitReason.STOP_LOSS:
            exit_fee = exit_dollar_amount * self.config.fees.taker_fee
        elif zone.position.exit_reason == ExitReason.TAKE_PROFIT:
            exit_fee = exit_dollar_amount * self.config.fees.maker_fee

        print(f"exit fee = {exit_fee}")

        if zone.is_demand:
            brutto = (zone.position.exit_price - avg_price) * zone.position.total_coins
        elif zone.is_supply:
            brutto = (avg_price - zone.position.exit_price) * zone.position.total_coins

        print(f"brutto = {brutto}")

        total_fees = entry_fees + exit_fee
        netto = brutto - total_fees

        print(f"total fees = {total_fees}")
        print(f"netto = {netto}")

        print(f"current capital = {self.current_capital}")

        self.current_capital = self.current_capital + netto

        print(f"current capital = {self.current_capital}")


    def _update_portfolio(self, zone: Zone) -> None:

        zone.stats = TradeStatistics()

        if zone.position.exit_price is None:
            raise ValueError(f"position is active, but not ended after 1000 hours, zone: {zone}", f"\n position: {zone.position}")

        avg_price = zone.position.average_entry_price
        entry_fees = zone.position.total_dollars * self.config.fees.maker_fee
        exit_dollar_amount = zone.position.exit_price * zone.position.total_coins

        # Exit fee depends on exit reason: taker for stop loss, maker for take profit
        if zone.position.exit_reason == ExitReason.STOP_LOSS:
            exit_fee = exit_dollar_amount * self.config.fees.taker_fee
        elif zone.position.exit_reason == ExitReason.TAKE_PROFIT:
            exit_fee = exit_dollar_amount * self.config.fees.maker_fee

        # Brutto P&L based on zone direction
        if zone.is_demand:
            brutto = (zone.position.exit_price - avg_price) * zone.position.total_coins
        elif zone.is_supply:
            brutto = (avg_price - zone.position.exit_price) * zone.position.total_coins

        # Netto = brutto minus all fees, update capital
        total_fees = entry_fees + exit_fee
        self.total_fees += total_fees
        netto = brutto - total_fees

        zone.stats.brutto = brutto
        zone.stats.netto = netto
        zone.stats.entry_fees = entry_fees
        zone.stats.exit_fee = exit_fee

        self.current_capital = self.current_capital + netto


    def get_summary(self):
        return {
            "ending_capital": self.current_capital,
            "total_fees": self.total_fees,
            "executed_zones": len(self.executed_zones),
            "unexecuted_zones": len(self.unexecuted_zones),
            "unfinished_zones": len(self.unfinished_zones),
            "entries_hit": self.executed_entries_count,
            "average_entry_hit": self.average_executed_entries_count,
            "win_rate": self.win_rate,
            "loss_rate": self.loss_rate,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "highest_win": self.highest_win,
            "highest_loss": self.highest_loss,
        }
    


        