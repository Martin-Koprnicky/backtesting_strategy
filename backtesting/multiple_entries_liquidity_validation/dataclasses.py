import pandas as pd
import numpy as np

from enum import Enum
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

class ZoneType(Enum):
    """Whether a zone is demand (bullish) or supply (bearish)"""
    DEMAND = "demand"
    SUPPLY = "supply"

class PatternType(Enum):
    """The six supply/demand zone patterns."""
    BR  = "base_rally"
    BD  = "base_drop"
    RBR = "rally_base_rally"
    RBD = "rally_base_drop"
    DBR = "drop_base_rally"
    DBD = "drop_base_drop"

class Direction(Enum):
    """Whether a movement is going up or down."""
    UP = "up"
    DOWN = "down"
    NONE = "none"

@dataclass
class Base:
    """Stores all info needed about base."""
    start_idx: int = None
    end_idx: int = None

    high: float = None
    low: float = None
    body_high: float = None     # Highest candle close across base candles
    body_low: float = None      # Lowest candle close across base candles

    candle_count: int = None
    price_range: float = None
    
    tightness_ratio: float = None   # base_total_range / base_first_candle_range

@dataclass
class MovementCandle:
    """Stores info about candle in movement."""
    position: int = None    # Order in movement
    range: float = None
    body_size: float = None
    timestamp: datetime = None
    strength_score: float = None

@dataclass
class CandleScores:
    """Stores scores about candle in movement."""
    weakest: float = None
    strongest: float = None
    average_with_strongest: float = None    # Mean including the strongest candle
    average_without_strongest: float = None # Mean excluding the strongest candle

@dataclass
class StrongMovementAfter:
    """Stores detailed info about movement after the base."""
    start_idx: int = None
    candle_count: int = None
    direction: Direction = None
    validation: bool = None
    candle_metrics: list[MovementCandle] = None
    candle_scores: CandleScores = None


    @property
    def is_upwards(self):
        return self.direction == Direction.UP
    
    @property
    def is_downwards(self):
        return self.direction == Direction.DOWN

@dataclass
class StrongMovementBefore:
    """Stores detailed info about movement before the base."""
    start_idx: int = None
    candle_count: int = None
    direction: Direction = None
    validation: bool = None
    candle_metrics: list[MovementCandle] = None
    candle_scores: CandleScores = None

    @property
    def is_upwards(self):
        return self.direction == Direction.UP
    
    @property
    def is_downwards(self):
        return self.direction == Direction.DOWN
    

@dataclass
class LQValidation:
    """Stores info about liquidity validation."""
    validation_time: datetime = None
    validation_index: int = None

@dataclass
class MovementAfter:
    """For debug purpose only."""
    check_direction: int = 0
    progressive_movement: int = 0
    candle_range: int = 0
    candle_strength: int = 0

@dataclass
class MovementBefore:
    """For debug purpose only."""
    check_direction: int = 0
    progressive_movement: int = 0
    candle_range: int = 0
    candle_strength: int = 0


class ExitReason(Enum):
    """Why close opened position."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"

@dataclass
class Entry:
    """Stores info about single entry in position."""
    level: float
    price: float
    risk: float
    coin_amount: float
    dollar_amount: float

    triggered: bool = False
    executed: bool = False
    execution_time: Optional[datetime] = None

@dataclass
class Position:
    """Represents an active trading position for a zone."""

    # Entry tracking
    entries: list[Entry] = None
    stop_loss: float = None
    take_profit: float = None

    entry_timestamp: datetime = None
    entry_index: int = None

    exit_price: float = None
    exit_reason: ExitReason = None
    exit_timestamp: datetime = None

    # 1R tracking
    one_r_range: float = None
    one_r_threshold: float = None
    one_r_threshold_triggered: bool = None
    
    # Extreme tracking (for 1R decline)
    highest_high: float = 0
    lowest_low: float = float('inf')

    total_fees: float = 0
    time_during_trade: int = 0


    @property
    def is_active(self) -> bool:
        return any(entry.executed for entry in self.entries)
    
    @property
    def total_coins(self) -> float:
        return sum(entry.coin_amount for entry in self.entries if entry.executed)

    @property
    def total_dollars(self) -> float:
        return sum(entry.dollar_amount for entry in self.entries if entry.executed)

    @property
    def average_entry_price(self) -> float:
        if self.total_coins == 0:
            return 0
        return self.total_dollars / self.total_coins

    @property
    def executed_entries_count(self) -> int:
        return sum(1 for entry in self.entries if entry.executed)
    
    @property
    def executed_entries_list(self):
        return [e for e in self.entries if e.executed is True]
    
    @property
    def ended(self) -> bool:
        if self.is_active and self.exit_price is not None:
            return True
        
@dataclass
class TradeStatistics:
    brutto: float = None
    netto: float = None
    entry_fees: float = None
    exit_fee: float = None

    @property
    def total_fees(self) -> float:
        return self.entry_fees + self.exit_fee
    

@dataclass
class Zone:
    """
    Main dataclass above all.

    Fully detected supply/demand zone with base, movements and
    liquidity validation.
    """
    type: ZoneType = None
    pattern: PatternType = None

    base: Base = None
    movement_after: StrongMovementAfter = None
    movement_before: StrongMovementBefore = None
    lq_validation: LQValidation = None
    position: Position = None
    stats: TradeStatistics = None

    # Some variables
    scan_window: pd.DataFrame = None
    time_before_entry: datetime = None
    
    @property
    def base_range(self) -> float:
        return self.base.high - self.base.low
    
    @property
    def is_demand(self) -> bool:
        return self.type == ZoneType.DEMAND
    
    @property
    def is_supply(self) -> bool:
        return self.type == ZoneType.SUPPLY
    
    @property
    def starting_entry_price(self) -> float:
        entry_prices = [entry.price for entry in self.position.entries]
        return max(entry_prices) if self.is_demand else min(entry_prices)

