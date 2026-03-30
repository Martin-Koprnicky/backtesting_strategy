"""
Pattern Detection
=================

???\
This was ass.. rewrite it..
???\

Detection Flow Shortly
----------------------
1. Base
    Code iterate through data, and if candles stay within certain range,
    they are considered as a base.

2. Strong Movement
    There are two movements, before and after. They measure if candles
    after or before or both, are strong enough, has big enough body, etc.
    If they are valid, zone move on to next validation.

3. Liquidity Validation
    Let's take example for demand. After strong movement after, price has to
    make a dip, below config.lq_percentage. Within this movement, price has to
    make at least one bearish candle. Then price has to reach new high.

    So even simplier: Price has to make high, then higher low, low enough,
    cannot touch base_high, then make new higher high, then it's validated.

4. Overlapping
    It removes overlapped zones, with their base indexes.

Detection Flow Detailed
-----------------------
1. Base
    At first, base must be found. So code iterate through each candle, 
    and based on pre-fixed rules, we find a base.

    In config there is a min and max candle count variable specified,
    and _find_base method is programmed in a way, that it will find ALL 
    bases possible. 
    
    On single candle, this method can find up to config.max_candle_count
    bases, which is way more that it needs to be. 
    (This will come to sense soon.)

    This is due to, we would not miss a chance of better strong movement, 
    or longer base. The longer base the better, but the stronger
    strong_movement the even better, they will cut each other later.

    Example:
        There are 5 candles in a row. All of them can fit into base.
        So we can find 5 different bases. First base with first candle, 
        second base with first and second candle, third base with first,
        second and third candle, and so on, up to fifth base.

        Now, imagine we gave into config so ridiculous variables, that
        fourth candle can fit into both base and strong movement.

        Now, our zones got divided. Suddenly third zone, with three base
        candles got validated with strong movement, but the rest didn't
        come through strong movement validation

        That's the real reason why we make all bases possible, which are 
        basically same. Cause we don't know which one will work.

        This will be reduced by overlapping method at the end, which
        will cut all zones around, based on their indexes.

2. Strong Movement
    There are two parts, strong movement before and after. Each of them has
    its own config, since they both need slightly different settings

    They both share the same methods, only the movements select, which of the
    methods are being used.

    Example:
        Movement after use more method such as _check_candles_range and
        _check_candles_strength, which is very useful. But movemenet 
        before uses only _check_candles_range, cause I found out that,
        we don't really care how strong the candles are into the base,
        we only care how strong they are when candles are leaving base.

    Now how this works.

    First of all, code finds out, for which patterns are we looking for, 
    from configuration.
    Second of all, code iterate through those patterns, and then through 
    the bases he found. So if base doesn't fit on Rally after base, it might 
    fit on Drop after base. Same story with movement before.

    Code have bases stored with start and end base_index, from those,
    code simply iterate through candles, and see if they fit.

    Each method has it's own iteration, so the methods can stay flexible.

    Example:
        Remember the example with 5 bases from single candle?
        Now, line 605, method _check_direction, this method is simply asking,
        if all candles in movement after are in same direction, if yes, 
        the zone is kept and zone continue on another validation, else, 
        it is invalidated, and no longer continue with other validations.

3. Liquidity Validation
    In this validation, price action has to follow, some set of rules.
    There are 3 phases, Looking phase, Retracement phase and Breakout phase.

    Let's consider a demand zone for this follow up explanation.

    Looking Phase:
        Code set High, which is variable that will be used later. If price
        goes higher, code update High with new High. With that, code is looking
        for one bearish candle, if there is, we move on phase two.

    Retracement Phase:
        This is not new candle, this is still that bearish candle, that pushed 
        code there. Code check if the candle's low, is low enough, in order 
        to make sufficient retracement. 
        
        Retracement is calculated from base.high up to High, we marked in 
        previous phase (can be updated within this phase also), code subtract it 
        from each other, and we get range. And if price retrace certain 
        percentage of this range, code moves onto third phase.

    Breakout Phase:
        In this phase, price has to only go up, and reach the High again.
        If it reaches, zone became fully validated.

    Price cannot touch zones base during any of these phases.

4. Overlapping Zones
    Now we've got the correct idea, why the code has that many bases, as a 
    pottential zones, we simply don't know which one will works. With that said
    we really need to get rid of the overlapping zones. So code track their base
    indexes, sort them by it, and if there are some, closer than 5 hours, 
    it removes them.
    
Usage:
------
    from strategy.pattern_detection import PatternDetector
    from data.data_handlers import get_data
    from strategy.config.log_config import load_config

    years = [2023, 2024]
    timeframes = ['1h', '5m', '1s']
    data = get_data(type='parquet', year=years, timeframes=timeframes)

    config = load_config()

    detector = PatternDetector(config, data)
    zones = detector.detect_patterns()
"""

import pandas as pd

from dataclasses import dataclass, field
from typing import Union, Optional
from enum import Enum
from datetime import datetime
from backtesting.multiple_entries_liquidity_validation.config.log_config import Config
from backtesting.multiple_entries_liquidity_validation.dataclasses import (
    ZoneType, PatternType, Direction, Zone, Base, StrongMovementBefore, 
    StrongMovementAfter, MovementCandle, CandleScores, MovementBefore, MovementAfter, 
    LQValidation
)

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    timestamp: pd.Timestamp

class PatternDetector:
    """
    Detect supply and demand zones with multi-stage validation process.

    How it works:
    -------------
    1. First of all, code find all bases possible
    2. Then bases are validated with strong movement before and after
    3. Then zones are validated with Liquidity Validation
    4. We get rid of the overlapping zones, with same or close indexes

    """
    def __init__(self, config: Config, data: pd.DataFrame, data_plus_month: pd.DataFrame = None):
        """
        Initialize the pattern detector

        Args:
            config : Entire strategy configuration
            data : Full year of OHLCV data
            data_plus_month : Full year plus next month of data
        """
        self._config = config
        self._data = data
        self._data_plus_month = data_plus_month

        # List of zones
        self._zones: list = []

        # For debug purpose only
        self._successful_validation_movement_before: MovementBefore = MovementBefore()
        self._successful_validation_movement_after: MovementAfter = MovementAfter()

    def detect_patterns(self):
        """
        Call different methods in order to find bases and validate zones.

        Returns
        -------
        zones : list of Zone objects
            List of validated supply/demand zones. Each zone contains pattern type, 
            zone boundaries (high/low prices and candle indices), movement validation 
            metrics (candle counts, strength scores), and liquidity validation timestamp.
            Returns empty list if no valid zones are found.
        """

        self._find_base()
        #print(f"Number of bases after base validation: {len(self._base_list)}")
        self._validate_strong_movements()
        #print(f"Number of bases after movement validation: {len(self._movement_validation_list)}")
        self._validate_liquidity()
        #print(f"Number of zones after liquidity validation: {len(self._liquidity_validation_list)}")
        self._kill_overlapping()
        #print(f"Number of zones after killing overlapping: {len(self._zones)}")

        return self._zones

    def _numpy_arrays(self, data: pd.DataFrame) -> dict:
        """
        Make numpy arrays from pandas DataFrame, for faster iteration.
        
        Args:
            data : Input of OHLCV data
        
        Returns:
            dict : keys: 'lows', 'highs', 'opens', 'closes', 'timestamps'
        """
        return {
            'opens': data['open'].values,
            'highs': data['high'].values,
            'lows': data['low'].values,
            'closes': data['close'].values,
            'timestamps': data.index.values
        }

    def _cut_numpy_arrays(self, start_index: int, end_index: int, np_arrays: dict) -> dict:
        """
        Makes a cut in a array, for using less data

        Args:
            start_index : Starting index of the cut
            end_index : Ending index of the cut
            np_arrays : Full numpy arrays, which are being cut

        Returns:
            dict : keys: 'lows', 'highs', 'opens', 'closes', 'timestamps'
        
        """
        return {
            'opens': np_arrays['opens'][start_index:end_index],
            'highs': np_arrays['highs'][start_index:end_index],
            'lows': np_arrays['lows'][start_index:end_index],
            'closes': np_arrays['closes'][start_index:end_index],
            'timestamps': np_arrays['timestamps'][start_index:end_index],
        }
    
    def _update_list(self, new_list: list[Zone]) -> None:
        """
        Updates self._zones list of current Zone objects.

        Args:
            new_list: New updated list of Zone objects
        """
        self._zones.clear()
        self._zones = new_list

    def _find_base(self) -> None:
        """System, that finds all possible bases."""

        # Set variables, numpy arrays as a data, count as a number of candles in a base, 
        # range as base range, empty valid_bases list
        arrays = self._numpy_arrays(self._data)
        count = self._config.base.candle_count
        range_ = self._config.base.max_range
        valid_bases = list()

        # Normalize count to list
        if isinstance(count, int):
            count_values = [count]
        else:
            count_values = list(range(count[0], count[1] + 1))

        # Iteration through count_values, count_values are boundaries for
        # min and max of candles in base length.
        # Could be 1, or 2, or 5, it depends on configuration
        for number in count_values:
            # Here is the iteration of all candles in a year, for a single count_value
            # If count value is 1, it will find bases of length 1, if value is 5, 
            # it will find bases of length 5
            # Some of bases can have identical base_index, it will be delt with later
            for candle in range(len(arrays['lows']) - number):

                # This cut gives me the exact number of candles I am checking for base
                np_arrays = self._cut_numpy_arrays(
                    start_index=candle,
                    end_index=candle+number,
                    np_arrays=arrays,
                )

                # Open up numpy arrays, for better readability
                opens = np_arrays['opens']
                highs = np_arrays['highs']
                lows = np_arrays['lows']
                closes = np_arrays['closes']

                # Reference high and low, is the high and low of first candle.
                # In config there is base_range variable in percentage value.
                # Boundaries of the base are how much can base candles move
                # from reference high and low by percentage.

                # If base_range in config would be 0.5 (50%), seconds candles
                # high could not be higher than first_candle_high + (first_candle_range * 0.5)
                # and could not be lower than first_candle_high - (first_candle_range * 0.5).
                # It is same with low, and the rest of candles

                reference_high = highs[0]
                reference_low = lows[0]

                tolerance = (reference_high - reference_low) * (range_ - 1.0)
                max_high = reference_high + tolerance
                min_high = reference_high - tolerance
                max_low = reference_low + tolerance
                min_low = reference_low - tolerance

                # Base become valid if all candles are within base_range boundaries

                valid_highs = (highs >= min_high) & (highs <= max_high)
                valid_lows = (lows >= min_low) & (lows <= max_low)
                base_is_valid = (valid_highs & valid_lows).all()

                if base_is_valid:
                    highest_high = max(highs)
                    lowest_low = min(lows)
                    highest_open_close = max(max(opens), max(closes))
                    lowest_open_close = min(min(opens), min(closes))

                    base_total_range = highest_high - lowest_low
                    first_candle_range = highs[0] - lows[0]

                    if first_candle_range == 0:
                        continue

                    base_tightness_ratio = base_total_range / first_candle_range

                    # At this stage, base is already valid, we only calculate some stuffs
                    # For better monitorig of Base object
                    base = Base(
                        start_idx=candle,
                        end_idx=candle + number - 1,
                        high=highest_high,
                        low=lowest_low,
                        body_high=highest_open_close,
                        body_low=lowest_open_close,
                        candle_count=len(valid_highs),
                        price_range=highest_high-lowest_low,
                        tightness_ratio=base_tightness_ratio,
                    )

                    # Movement after and before are created here, with starting index
                    movement_after = StrongMovementAfter(
                        start_idx=candle + number
                    )

                    movement_before = StrongMovementBefore(
                        start_idx=candle - 1
                    )

                    # So as Zone object, the upper dataclass that holds everything
                    zone = Zone(
                        base=base,
                        movement_after=movement_after,
                        movement_before=movement_before,
                    )

                    # Zone is appended to valid_bases
                    valid_bases.append(zone)

        # The zone list gets updated with new list as valid_bases
        self._update_list(new_list=valid_bases)

    def _validate_strong_movements(self) -> None:
        """System for validating strong movement before and after the base."""

        valid_zones = list()

        # Iteration starts with patterns, so we could make the code to look for
        # certain patterns, specified in configuration, not the other way around
        for pattern in self._config.general.patterns:
            for zone in self._zones:

                # Movement after validation is for all patterns, so we start with that
                self._validate_movement_after(zone)

                # If zone got invalidated, we move on.
                if zone.movement_after.validation is False:
                    continue

                # Set variable for validated movement after the base
                movement_after = zone.movement_after

                # For base rally and base drop patterns, we only need validation after
                # Once the movement_after is validated, we assign zone type and 
                # pattern type to zone
                if pattern in ['BR', 'BD']:

                    if pattern == 'BR' and movement_after.is_upwards:
                        zone.type = ZoneType.DEMAND
                        zone.pattern = PatternType.BR
                        valid_zones.append(zone)

                    elif pattern == 'BD' and movement_after.is_downwards:
                        zone.type = ZoneType.SUPPLY
                        zone.pattern = PatternType.BD
                        valid_zones.append(zone)

                # If pattern type has movement before also, we continue here
                elif pattern in ['RBR', 'DBD', 'RBD', 'DBR']:
                    
                    # Validation for movement before
                    self._validate_movement_before(zone)

                    # If zone got invalidated, continue
                    if zone.movement_before.validation is False:
                        continue
                    
                    # Set variable for validated movement before the base
                    movement_before = zone.movement_before

                    # Once both movement are validated, zone type and pattern type is assigned to zone
                    # Code uses here tripple check, to make sure, no mistakes happens during assigning
                    if pattern == 'RBR' and movement_before.is_upwards and movement_after.is_upwards:
                        zone.type = ZoneType.DEMAND
                        zone.pattern = PatternType.RBR
                        valid_zones.append(zone)

                    elif pattern == 'DBD' and movement_before.is_downwards and movement_after.is_downwards:
                        zone.type = ZoneType.SUPPLY
                        zone.pattern = PatternType.DBD
                        valid_zones.append(zone)

                    elif pattern == 'RBD' and movement_before.is_upwards and movement_after.is_downwards:
                        zone.type = ZoneType.SUPPLY
                        zone.pattern = PatternType.RBD
                        valid_zones.append(zone)

                    elif pattern == 'DBR' and movement_before.is_downwards and movement_after.is_upwards:
                        zone.type = ZoneType.DEMAND
                        zone.pattern = PatternType.DBR
                        valid_zones.append(zone)

        # Code updates list with valid zones
        self._update_list(valid_zones)

    def _validate_strong_movementss(self) -> None:
        """This method is for debug only."""

        valid_zones = list()
        single_after_validation = 0
        single_before_validation = 0
        both_before_and_after_validation = 0

        for zone in self._zones:

            self._validate_movement_after(zone)
            self._validate_movement_before(zone)

            if zone.movement_after.validation is True and zone.movement_before.validation is False:
                single_after_validation += 1
            elif zone.movement_before.validation is True and zone.movement_after.validation is False:
                single_before_validation += 1
            elif zone.movement_after.validation is True and zone.movement_before.validation is True:
                both_before_and_after_validation += 1
            else:
                continue
            
            if zone.movement_after.validation is False:
                continue
            elif zone.movement_before.validation is False:
                continue
        
            movement_after = zone.movement_after
            movement_before = zone.movement_before

            if movement_before.is_upwards and movement_after.is_upwards:
                zone.type = ZoneType.DEMAND
                zone.pattern = PatternType.RBR
                valid_zones.append(zone)

            elif movement_before.is_downwards and movement_after.is_downwards:
                zone.type = ZoneType.SUPPLY
                zone.pattern = PatternType.DBD
                valid_zones.append(zone)

            elif movement_before.is_upwards and movement_after.is_downwards:
                zone.type = ZoneType.SUPPLY
                zone.pattern = PatternType.RBD
                valid_zones.append(zone)

            elif movement_before.is_downwards and movement_after.is_upwards:
                zone.type = ZoneType.DEMAND
                zone.pattern = PatternType.DBR
                valid_zones.append(zone)

        self._update_list(valid_zones)
        
        print(f"Single after validations: {single_after_validation}")
        print(f"Single before validations: {single_before_validation}")
        print(f"Both before and after validations: {both_before_and_after_validation}")
        
    def _validate_movement_after(self, zone: Zone) -> None:
        """System, that validates movement after the base."""

        # Set variables, numpy arrays, configuration and movement after dataclass
        arrays = self._numpy_arrays(self._data)
        config = self._config.movement_after
        movement = zone.movement_after
        
        # If int, normalize count to list
        if isinstance(config.candle_count, int):
            candle_count_values = [config.candle_count]
        else:
            candle_count_values = list(range(config.candle_count[0], config.candle_count[1] + 1))

        # Set starting index and ending index of the movement
        start_idx = movement.start_idx
        end_idx = start_idx + candle_count_values[-1]

        # Check bounds
        if end_idx > len(arrays['highs']):
            movement.validation = False
            return

        # Cut npmpy arrays based on indexes
        cut_arrays = self._cut_numpy_arrays(start_idx, end_idx, arrays)

        # Validation with candle direction and candle count
        self._check_direction(movement, cut_arrays, candle_count_values)

        if config.progressive_movement is True:
            # Validation with progressive movement
            self._check_progressive_movement(movement, cut_arrays)
        
        # Validation with and candle range and sizes
        self._check_candles_range(zone, movement, cut_arrays, config)
        
        # Validation with candle strength
        self._check_candles_strength(zone, movement, config)


    def _validate_movement_before(self, zone: Zone) -> None:
        """System, that validates movement before the base."""

        # Set variables, numpy arrays, configuration and movement before dataclass
        arrays = self._numpy_arrays(self._data)
        config = self._config.movement_before
        movement = zone.movement_before

        # If int, normalize count to list
        if isinstance(config.candle_count, int):
            candle_count_values = [config.candle_count]
        else:
            candle_count_values = list(range(config.candle_count[0], config.candle_count[1] + 1))

        # Set starting index and ending index of the movement
        start_idx = movement.start_idx
        end_idx = start_idx - candle_count_values[-1]

        # Check bounds
        if end_idx < 0:
            movement.validation = False
            return
        
        # Cut npmpy arrays based on indexes
        cut_arrays = self._cut_numpy_arrays(end_idx, start_idx, arrays)

        # Validation with candle direction and candle count
        self._check_direction(movement, cut_arrays, candle_count_values)
        
        if config.progressive_movement is True:
            # Validation with progressive movement
            self._check_progressive_movement(movement, cut_arrays)

        # Validation with and candle range and sizes
        self._check_candles_range(zone, movement, cut_arrays, config)
        
        """
        # Validation with candle strength
        self._check_candles_strength(zone, movement, config_)
        """
        
    def _check_direction(self, movement: Union[StrongMovementAfter, StrongMovementBefore], cut_arrays: dict, candle_count_values: list) -> None:
        """
        Checks out the direction, and how many candles stays within the direction.

        Args:
            movement : Which movement, after of before the base
            cut_arrays : Cut numpy arrays, data for iteration
            candle_count_values : How many candles are we checking out
        """
        
        # Open up numpy arrays, for better readability
        opens = cut_arrays['opens']
        closes = cut_arrays['closes']

        # Movement validation is set out to be True, if nothing happens,
        # it remains True, if something interfere with validation,
        # it will be set on False
        movement.validation = True

        # Check if candles are same direction in movement after
        # We also validate if the candle_count is sufficient
        for value in candle_count_values[::-1]:

            candle_types = list()
            broken = False

            # Code sorts out type of candles, bullish and bearish
            for i in range(value):
                if closes[i] > opens[i]:
                    candle_types.append(1)
                elif closes[i] < opens[i]:
                    candle_types.append(0)
                else:
                    broken = True
                    break
            
                # If candles are in same direction so far
                # if not, it's invalidated
                if len(set(candle_types)) != 1:
                    broken = True
                    break

            # If not broken, the direction is validated so far
            if broken is False:
                movement.candle_count = value
                movement.direction = Direction.UP if set(candle_types) == {1} else Direction.DOWN
                break

        # If direction is still un-set, movement gets invalidated
        if movement.direction is None:
            movement.validation = False
            return

        
    def _check_progressive_movement(self, movement: Union[StrongMovementAfter, StrongMovementBefore], cut_arrays: dict) -> None:
        """
        Checks out progressive movement, if candles are making progressive highs
        or progressive lows.
        
        Args:
            movement : Which movement, after of before the base
            cut_arrays : Cut numpy arrays, data for iteration
        """

        # Movement validation was set to True last time, now we only ask if it's false
        if movement.validation is False:
            return
        
        # Open up numpy arrays, for better readability
        highs = cut_arrays['highs']
        lows = cut_arrays['lows']

        # Check progressive movement
        # If all consecutive candles has higher highs or lower lows then previous ones
        if movement.is_upwards:
            for i in range(1, movement.candle_count):
                if highs[i] <= highs[i-1]:
                    movement.validation = False
                    return

        elif movement.is_downwards:
            for i in range(1, movement.candle_count):
                if lows[i] >= lows[i-1]:
                    movement.validation = False
                    return
        

    def _check_candles_range(self, zone: Zone, movement: Union[StrongMovementAfter, StrongMovementBefore], cut_arrays: dict, config: Config) -> None:
        """
        Checks out candles range in the movement.

        Args:
            zone : Which zones candles
            movement : Which movement, after of before the base
            cut_arrays : Cut numpy arrays, data for iteration
            candle_count_values : How many candles are we checking out
        """
        
        # Return if movement validation is already False
        if movement.validation is False:
            return
        
        # Open up numpy arrays, for better readability
        opens = cut_arrays['opens']
        highs = cut_arrays['highs']
        lows = cut_arrays['lows']
        closes = cut_arrays['closes']
        timestamps = cut_arrays['timestamps']

        # Set variables, candle_metrics as a list, single_count as a bool
        movement.candle_metrics = list()
        is_single_count = movement.candle_count == 1

        for i in range(movement.candle_count):
            # Calculating body size and range of current candle in movement
            candle_range = highs[i] - lows[i]
            candle_body = abs(closes[i] - opens[i])

            # Range size requirement
            if isinstance(config.movement_range, (float, int)):
                range_is_valid = candle_range >= (zone.base_range * config.movement_range)
            elif isinstance(config.movement_range, list):
                range_is_valid = (zone.base_range * config.movement_range[0]) <= candle_range <= (zone.base_range * config.movement_range[1])

            # Body size requirement
            body_is_valid = candle_body >= (candle_range * config.body_min_percentage)

            # If not both are valid, the zone is getting invalidated
            if not (range_is_valid and body_is_valid):
                # If first candle failed, the whole movement if invalid
                if i == 0 or is_single_count:
                    movement.validation = False
                    return
                # Else, a later candle (i > 0) failed, but the movement is still valid,
                # just with fever candles, anyway, stop collecting
                else:
                    return

            # Store a candle info into movement_candle
            candle = MovementCandle(
                position=i+1,
                range=candle_range,
                body_size=candle_body,
                timestamp=timestamps[i]
            )

            # Extend the whole movement with this candle
            movement.candle_metrics.append(candle)


    def _check_candles_strength(self, zone: Zone, movement: Union[StrongMovementAfter, StrongMovementBefore], config: Config) -> None:
        """
        Checks out candles strengths in the movement.
        
        Args:
            zone : Which zones candles
            movement : Which movement, after of before the base
            config : Movement configuration
        """

        # Return if movement validation is already False
        if movement.validation is False:
            return
        
        # Calculation of candle strength score
        for candle in movement.candle_metrics:
            candle.strength_score = ((candle.range/zone.base_range) * 0.8) + ((candle.body_size/candle.range) * 0.2)

        # Set calculations, all_scores list, the weakest and the strongest scores in the list
        all_scores = [candle.strength_score for candle in movement.candle_metrics]
        weakest_score = min(all_scores)
        strongest_score = max(all_scores)
        
        # Store candle scores into movement
        candle_scores = CandleScores(
            weakest=weakest_score,
            strongest=strongest_score,
            average_with_strongest=sum(all_scores) / len(all_scores),
            average_without_strongest=(sum(all_scores) - strongest_score) / (len(all_scores) - 1) if len(all_scores) > 1 else 0
        )

        movement.candle_scores = candle_scores

        # If scores are sufficient enough continue, else, zones gets invalidated
        if weakest_score < config.min_weakest_candle_strength_score or strongest_score < config.min_strongest_candle_strength_score:
            movement.validation = False
            return

    def _validate_liquidity(self) -> None:
        """Liquidity validation."""

        if self._config.liquidity.validation == False:
            return

        # If we have data plus month, we use that, because some of zones
        # could be validated in next year, but we woudn't have that data for it
        # else, full current year of data
        if self._data_plus_month is not None:
            data = self._data_plus_month
        else:
            data = self._data
        
        # Set variables, liquidity configuration, empty valid_zones list
        config = self._config.liquidity
        valid_zones = list()

        # If there are no zones for validation, return 
        if not self._zones:
            return

        # Iteration through zones, waiting for lq validation
        for zone in self._zones:

            # Set variables, zone start and end indexes, and numpy arrays as candles
            val_start_index = zone.movement_after.start_idx
            val_end_index = min(val_start_index + config.timeout_hours, len(data))
            arrays = self._numpy_arrays(data=data.iloc[val_start_index:val_end_index])

            # Set more variables, 
            high = None     # Highest High
            low = None      # Higher Low

            # Zone has to pass all of these three phases.
            # Logic behind it is explained in file doc-string.
            LOOKING_PHASE = True
            RETRACEMENT_PHASE = False
            BREAKOUT_PHASE = False

            def _update_high(candle_high: float) -> None:
                """Update highest high since movement after."""
                nonlocal high
                if high is None or candle_high > high:
                    high = candle_high

            def _update_low(candle_low: float) -> None:
                """Update lowest low since movement after."""
                nonlocal low
                if low is None or candle_low < low:
                    low = candle_low

            def _ddip() -> float:
                """Calculate dip retracement for demand."""

                higher_range = high - zone.base.high
                lower_range = low - zone.base.high
                return 1 - (lower_range / higher_range)
            
            def _sdip() -> float:
                """Calculate dip retracement for supply."""
                higher_range = zone.base.low - low
                lower_range = zone.base.low - high
                return 1 - (lower_range / higher_range)

            for i in range(len(arrays['lows'])):

                # Open up numpy arrays, for better readability
                candle_open = arrays['opens'][i]
                candle_high = arrays['highs'][i]
                candle_low = arrays['lows'][i]
                candle_close = arrays['closes'][i]
                candle_timestamp = arrays['timestamps'][i]

                bullish = candle_close > candle_open
                bearish = candle_close < candle_open


                # Split onto supply and demand strategy
                if zone.is_demand:

                    # If candle low touch the zones base, discard the zone
                    if i != 0 and candle_low < zone.base.high:
                        break

                    # Looking Phase is open, checking for first bearish candle
                    # and still looking for new highs
                    if LOOKING_PHASE:
                        _update_high(candle_high)
                        
                        if bearish:
                            # Continue with RETRACEMENT PHASE, with this candle, 
                            # zone can qualify for BREAKOUT PHASE
                            LOOKING_PHASE = False
                            RETRACEMENT_PHASE = True

                    # Retracement Phase is open, checking for new lows and highs
                    if RETRACEMENT_PHASE:
                        _update_low(candle_low)

                        if bullish and candle_high > high:
                            high = candle_high
                            low = None
                            RETRACEMENT_PHASE = False
                            LOOKING_PHASE = True
                            continue

                        # Calculating retracement every candle
                        # Set variables, highest high - base high as high_range, 
                        # lower high - base high as low range, retracement movement by percentage

                        # If retracement is enough
                        if config.retracement_percentage_max > _ddip() > config.retracement_percentage_min:
                            # We want continue with loop, cause only with next candle the zone can be qualified
                            RETRACEMENT_PHASE = False
                            BREAKOUT_PHASE = True
                            continue

                    # Breakout Phase is open
                    if BREAKOUT_PHASE:
                        _update_low(candle_low)

                        # Recalculate retracement variable
                        # Checking if retracement didn't go too low, getting too close to the zones base,
                        # could be bad for the zone
                        if config.retracement_percentage_max < _ddip():
                            break

                        # Checking if price broke the highest high
                        if bullish and candle_high > high:
                            zone.lq_validation = LQValidation(
                                validation_time=candle_timestamp,
                                validation_index=i
                            )
                            # Append valid zone to a list
                            valid_zones.append(zone)
                            break

                elif zone.is_supply:

                    # If candle high touch the zones base, discard the zone
                    if i != 0 and candle_high > zone.base.low:
                        break

                    # Looking Phase is open, checking for first bullish candle,
                    # and still looking for new lows
                    if LOOKING_PHASE is True:
                        _update_low(candle_low)

                        if bullish:
                            # Continue with RETRACEMENT PHASE, with this candle, 
                            # zone can qualify for BREAKOUT PHASE
                            LOOKING_PHASE = False
                            RETRACEMENT_PHASE = True

                    # Retracement Phase is open, checking for new highs and lows
                    if RETRACEMENT_PHASE is True:
                        _update_high(candle_high)

                        if bearish and candle_low < low:
                            low = candle_low
                            high = None
                            RETRACEMENT_PHASE = False
                            LOOKING_PHASE = True
                            continue

                        # Calculating retracement every candle
                        # Set variables, base low - lowest low as high_range, 
                        # base low - higher low as low range, retracement movement by percentage

                        # If retracement is enough
                        if config.retracement_percentage_max > _sdip() > config.retracement_percentage_min:
                            # We want continue with loop, cause only with next candle the zone can be qualified
                            RETRACEMENT_PHASE = False
                            BREAKOUT_PHASE = True
                            continue
                    
                    # Breakout Phase is open
                    if BREAKOUT_PHASE is True:
                        _update_high(candle_high)
                        # recalculating retracement variables
                        # Checking if retracement didn't go too high, getting too close to the zones base,
                        # could be bad for the zone
                        if config.retracement_percentage_max < _sdip():
                            break

                        # Checking if price broke the lowest low
                        if bearish and candle_low < low:
                            zone.lq_validation = LQValidation(
                                validation_time=candle_timestamp,
                                validation_index=i
                            )
                            # Append valid zone to a list
                            valid_zones.append(zone)
                            break

        # Zone list gets updated with new list of valid zones
        self._update_list(valid_zones)


    def _kill_overlapping(self) -> None:
        """System that kills overlapping zones with close indexes, as sign of sharing same base candles."""

        # Set variables, empty list, sorted current zone list by starting index, varible for indexes
        valid_zones = list()
        zone_list = sorted(self._zones, key=lambda zone: zone.base.start_idx)
        last_zone_idx = 0

        # Loop through current sorted zone list
        for zone in zone_list:
            # Ask if current zone index is not closer than 5 candles than last zone index
            if zone.base.start_idx <= last_zone_idx + 5:
                continue
            # If not, zone is valid
            else:
                # Append to valid zones, and set current index as new last for next comparing
                valid_zones.append(zone)
                last_zone_idx = zone.base.start_idx

        # Zone list gets updated with new list of valid zones
        self._update_list(valid_zones)
