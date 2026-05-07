"""
Measurements
============

Purpose of this file is to measure price action after entry during certaion scenarios. 
One of the scenario is for example, price ripping through the zone in single candle, 
therefore executing entry and stop loss in single hour. I am trying to understand,
why does this happen, and if it's there any way how to prevent the execution at all.

Scenarios:
----------
1. Sharp Wick
    When there is small body, long wicks candle.
    Trying to understand if there are some coincidences where does the small body lies,
    in the candle, and if it has any impact on the price action.

2. Full Zone Retest
    When large candle rip through the zone instantly with single attempt.
    Then I will try to observe price action, and how are the chances of price to recover,
    and end up in our favour

3. Choppiness
    ...

"""

import pandas as pd
import numpy as np
import csv

from datetime import datetime
from dataclasses import dataclass, field
from typing import Union, Optional
from enum import Enum
from prettytable import PrettyTable

from data.numpy import numpy_arrays, cut_numpy_arrays
from data.data_handlers import get_data
from backtesting.multiple_entries_liquidity_validation.dataclasses import PatternType
from backtesting.multiple_entries_liquidity_validation.visualizations.visualizer import BacktestVisualizer



class SharpWickQuarters(Enum):
    """Where the body in sharp wick is placed."""
    FIRST = 1     # 0-25% in the candle away from the zone
    SECOND = 2    # 25-50% in the candle away from the zone
    THIRD = 3     # 50-75% in the candle away from the zone
    FOURTH = 4    # 75-100% in the candle away from the zone

    def __lt__(self, other):
        return self.value < other.value

@dataclass
class SharpWick:
    """Measures for zone if Sharp Wick."""
    is_sharp_wick: bool = False
    sharp_wick_quarters: SharpWickQuarters = None
    sharp_wick_body_pct: float = None

@dataclass
class FullRetest:
    """Measures for zone if Full Zone Retest."""
    hello: int = None

@dataclass
class Part:
    """First part of the execution. First 10. hours."""
    highest_upward: float = None
    highest_downward: float = None

@dataclass
class SMA:
    changes: int = None
    highest_throughout_indexes: float = None
    lowest_throughout_indexes: float = None

@dataclass
class Indicators:
    first_half: Part = field(default_factory=Part)
    second_half: Part = field(default_factory=Part)
    sma_5: SMA = field(default_factory=SMA)
    sma_10: SMA = field(default_factory=SMA)
    sma_20: SMA = field(default_factory=SMA)

@dataclass
class Zone:
    """Zone for current measurements."""
    year: int
    pattern: str
    pnl: float
    high: float
    low: float
    entry_timestamp: pd.Timestamp
    
    sharp_wick: SharpWick = field(default_factory=SharpWick)
    full_retest: FullRetest = field(default_factory=FullRetest)

    indicators: Indicators = field(default_factory=Indicators)

    @property
    def is_demand(self) -> bool:
        return self.pattern in ['PatternType.DBR', 'PatternType.RBR']
    
    @property
    def is_supply(self) -> bool:
        return self.pattern in ['PatternType.DBD', 'PatternType.RBD']
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
@dataclass
class CurrentZones:
    """List of zones that were tested, so I could print them out."""
    winners: list[Zone] = field(default_factory=list)
    losers: list[Zone] = field(default_factory=list)
    

def read_csv():
    """CSV reader, opens csv file of zones to measure."""
    with open('backtesting/multiple_entries_liquidity_validation/measure_zones.csv') as file:
        reader = csv.DictReader(file)
        zones = []

        for zone in reader:
            if zone['year'] == 'year':
                continue
            zones.append(Zone(
                year=int(f"{zone['year']}"),
                pattern=zone['pattern'],
                pnl=round(float(zone['pnl']),2),
                high=round(float(zone['zone_high']),2),
                low=round(float(zone['zone_low']),2),
                entry_timestamp=pd.Timestamp(zone['entry_timestamp'])
            ))

    return zones


class Measurements:
    def __init__(self, data: pd.DataFrame, year):
        self.data = data
        self.data_1h = data['1h']
        self.year = year

        self.count = 0
        self.current = CurrentZones()

    def run(self):
        winners, losers = self._full_zone_retest()
        #self.plot_measurements(zones)
        return winners, losers

    def plot_measurements(self, zones: list[Zone]):
        visualizer = BacktestVisualizer.__new__(BacktestVisualizer)
        visualizer._data_1h = self.data_1h
        visualizer.plot_measurements(zones)

    def _sharp_wick(self) -> dict:
        zones = read_csv()

        current = CurrentZones()

        for zone in zones:
            if zone.year == self.year:
                self._measure_sharp_wick(zone)
                if zone.sharp_wick.sharp_wick_quarters is not None:
                    current.zones.append(zone)

        print(self.count)
        zns = sorted(current.zones, key=lambda zone: zone.sharp_wick.sharp_wick_quarters, reverse=True)
        fourth_avg = 0
        fourth_count = 0
        third_avg = 0
        third_count = 0
        second_avg = 0
        second_count = 0
        first_avg = 0
        first_count = 0
        for zone in zns:
            sw = zone.sharp_wick
            print(zone.year, sw.sharp_wick_quarters, zone.pnl)
            if sw.sharp_wick_quarters == SharpWickQuarters.FOURTH:
                fourth_avg += zone.pnl
                fourth_count += 1
            elif sw.sharp_wick_quarters == SharpWickQuarters.THIRD:
                third_avg += zone.pnl
                third_count += 1
            elif sw.sharp_wick_quarters == SharpWickQuarters.SECOND:
                second_avg += zone.pnl
                second_count+= 1
            elif sw.sharp_wick_quarters == SharpWickQuarters.FIRST:
                first_avg += zone.pnl
                first_count += 1
            

        print(f'\nFourth average: {fourth_avg}',f'\nThird average: {third_avg}',f'\nSecond average: {second_avg}')
        
        return {
            'count':self.count,
            'fourth':round((fourth_avg)/fourth_count,2) if fourth_count else 0.0,
            'third':round((third_avg)/third_count,2) if third_count else 0.0,
            'second':round((second_avg)/second_count,2) if second_count else 0.0,
            'first':round((first_avg)/first_count,2) if first_count else 0.0
        }

    def _measure_sharp_wick(self, zone: Zone) -> bool:
        start = self.data_1h.index.get_indexer([zone.entry_timestamp], method='nearest')[0]
        end = start + 50
        arrays = cut_numpy_arrays(start, end, numpy_arrays(self.data_1h))

        open, high, low, close, timestamp = (arrays[f'{t}'][0] for t in arrays.keys())

        bullish = open < close
        bearish = open > close

        candle_range = high - low
        body_range = abs(close - open)

        body_pct = (body_range / candle_range) * 100
        zone.sharp_wick.sharp_wick_body_pct = body_pct

        upper_range = high - (close if bullish else open)
        lower_range = (open if bullish else close) - low

        upper_range_pct = (upper_range / candle_range) * 100
        lower_range_pct = (lower_range / candle_range) * 100

        upper_boundary_pct = 100 - upper_range_pct
        lower_boundary_pct = lower_range_pct

        if body_pct < 100:
            self.count += 1
            if zone.is_demand:
                middle_pct = (upper_boundary_pct + lower_boundary_pct) / 2
            elif zone.is_supply:
                middle_pct = 100 - ((upper_boundary_pct + lower_boundary_pct) / 2)

            if 0 < middle_pct <= 25:
                zone.sharp_wick.sharp_wick_quarters = SharpWickQuarters.FIRST
            elif 25 < middle_pct <= 50:
                zone.sharp_wick.sharp_wick_quarters = SharpWickQuarters.SECOND
            elif 50 < middle_pct <= 75:
                zone.sharp_wick.sharp_wick_quarters = SharpWickQuarters.THIRD
            elif 75 < middle_pct <= 100:
                zone.sharp_wick.sharp_wick_quarters = SharpWickQuarters.FOURTH
            else:
                zone.sharp_wick.sharp_wick_quarters = None
                raise ValueError(f'Something wrong here. middle_pct: {middle_pct}')

        #calculate the middle of the body, and try out, which selection has the closest edges

    def _full_zone_retest(self) -> dict:
        zones = read_csv()

        table = PrettyTable()
        table.field_names = [
            'FH - Downwards', 'FH - Upwards', 
            'SH - Downwards', 'SH - Upwards',
            'SMA 5 - changes', 'SMA 20 - changes', 
            'SMA 5 - highest', 'SMA 5 - lowest',
            'SMA 20 - highest','SMA 20 - lowest'
            ]
        
        zones.sort(key=lambda zone: zone.pnl, reverse=True)
        
        for zone in zones:
            if zone.year == self.year:
                result = self._measure_full_zone_retest(zone)
                if result is not None:
                    if zone.pnl > 0:
                        self.current.winners.append(zone)
                    elif zone.pnl <= 0:
                        self.current.losers.append(zone)
                    """table.add_row([
                        zone.indicators.first_half.highest_downward,
                        zone.indicators.first_half.highest_upward,
                        zone.indicators.second_half.highest_downward,
                        zone.indicators.second_half.highest_upward,
                        zone.indicators.sma_5.changes,
                        zone.indicators.sma_20.changes,
                        zone.indicators.sma_5.highest_throughout_indexes,
                        zone.indicators.sma_5.lowest_throughout_indexes,
                        zone.indicators.sma_20.highest_throughout_indexes,
                        zone.indicators.sma_20.lowest_throughout_indexes
                    ])"""

        return self.current.winners, self.current.losers

        table.add_row([
            round(np.average([zone.indicators.first_half.highest_downward for zone in self.current.winners]),2),
            round(np.average([zone.indicators.first_half.highest_upward for zone in self.current.winners]),2),
            round(np.average([zone.indicators.second_half.highest_downward for zone in self.current.winners]),2),
            round(np.average([zone.indicators.second_half.highest_upward for zone in self.current.winners]),2),
            round(np.average([zone.indicators.sma_5.changes for zone in self.current.winners]),2),
            round(np.average([zone.indicators.sma_20.changes for zone in self.current.winners]),2),
            round(np.average([zone.indicators.sma_5.highest_throughout_indexes for zone in self.current.winners]),2),
            round(np.average([zone.indicators.sma_5.lowest_throughout_indexes for zone in self.current.winners]),2),
            round(np.average([zone.indicators.sma_20.highest_throughout_indexes for zone in self.current.winners]),2),
            round(np.average([zone.indicators.sma_20.lowest_throughout_indexes for zone in self.current.winners]),2)
        ])

        table.add_row([
            round(np.average([zone.indicators.first_half.highest_downward for zone in self.current.losers]),2),
            round(np.average([zone.indicators.first_half.highest_upward for zone in self.current.losers]),2),
            round(np.average([zone.indicators.second_half.highest_downward for zone in self.current.losers]),2),
            round(np.average([zone.indicators.second_half.highest_upward for zone in self.current.losers]),2),
            round(np.average([zone.indicators.sma_5.changes for zone in self.current.losers]),2),
            round(np.average([zone.indicators.sma_20.changes for zone in self.current.losers]),2),
            round(np.average([zone.indicators.sma_5.highest_throughout_indexes for zone in self.current.losers]),2),
            round(np.average([zone.indicators.sma_5.lowest_throughout_indexes for zone in self.current.losers]),2),
            round(np.average([zone.indicators.sma_20.highest_throughout_indexes for zone in self.current.losers]),2),
            round(np.average([zone.indicators.sma_20.lowest_throughout_indexes for zone in self.current.losers]),2)
        ])

        print(table)
                
        

    def _measure_full_zone_retest(self, zone: Zone) -> bool:
        start = self.data_1h.index.get_indexer([zone.entry_timestamp], method='nearest')[0]
        end = start + 50
        arrays = cut_numpy_arrays(start, end, numpy_arrays(self.data_1h))

        open, high, low, close, timestamp = (arrays[f'{t}'][0] for t in arrays.keys())

        ripped = True

        if zone.is_demand and low < zone.low:
            ripped = True
        elif zone.is_supply and high > zone.high:
            ripped = True

        if ripped is True:
            #print("-"*5, "Demand" if zone.is_demand else "Supply", "-"*5, f"P&L: {zone.pnl}", "-"*86)

            indexes = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
            sma_periods = [5, 10, 20]
            downwards_all = {}
            upwards_all = {}
            sma_values_ = {p: {} for p in sma_periods}

            for i in indexes:
                opens, highs, lows, closes, timestamps = (arrays[f'{t}'][0:i] for t in arrays.keys())
                highest_high, lowest_low = self._find_high_and_low(highs, lows)
                upwards_all[i], downwards_all[i] = self._calculate_distance_from_zone(zone, highest_high, lowest_low)

                for p in sma_periods:
                    if i >= p:
                        opens, highs, lows, closes, timestamps = (arrays[f'{t}'][i-p:i] for t in arrays.keys())
                        sma_values_[p][i] = self._calculate_distance_sma(zone, np.average([closes]))
                    else:
                        sma_values_[p][i] = 0.0

            idx = 15

            zone.indicators.first_half.highest_downward = max(val for index, val in downwards_all.items() if index <= idx)
            zone.indicators.first_half.highest_upward = max(val for index, val in downwards_all.items() if index >= idx)
            zone.indicators.second_half.highest_downward = max(val for index, val in upwards_all.items() if index <= idx)
            zone.indicators.second_half.highest_upward = max(val for index, val in upwards_all.items() if index >= idx)

            zone.indicators.sma_5.highest_throughout_indexes = max(sma for sma in sma_values_[5].values())
            zone.indicators.sma_5.lowest_throughout_indexes = min(sma for sma in sma_values_[5].values())
            
            zone.indicators.sma_20.highest_throughout_indexes = max(sma for sma in sma_values_[20].values())
            zone.indicators.sma_20.lowest_throughout_indexes = min(sma for sma in sma_values_[20].values())

            # Let's calculate SMA changes of direction over period of time..
            opens, highs, lows, closes, timestamps = (arrays[f'{t}'] for t in arrays.keys())
            sma_periods = [5, 10, 20]
            sma_values = {p: [] for p in sma_periods}
            sma_changes = {p: 0 for p in sma_periods}
            
            for i in range(len(lows)):
                for p in sma_periods:
                    if i >= p:
                        sma_values[p].append(np.average(closes[i-p:i]))

            # Direction, 1 is bullish, 0 is bearish
            for p in sma_periods:
                direction = None
                for i in range(1, len(sma_values[p])):
                    if sma_values[p][i] > sma_values[p][i-1]:
                        new_dir = 1
                    elif sma_values[p][i] < sma_values[p][i-1]:
                        new_dir = 0
                    else:
                        continue

                    if direction is not None and new_dir != direction:
                        sma_changes[p] += 1
                    direction = new_dir

            for p in sma_periods:
                continue
                print(f'SMA {p} changes: {sma_changes[p]}')

            zone.indicators.sma_5.changes = sma_changes[5]
            zone.indicators.sma_20.changes = sma_changes[20]

            return True

        return None
        
    def _find_high_and_low(self, highs: list[float], lows: list[float]) -> tuple[float, float]:
            """Finds highest high and lowest low in a array of candles."""
            highest_high = 0
            lowest_low = float('inf')

            for i in range(len(lows)):
                if lows[i] < lowest_low:
                    lowest_low = lows[i]
                
                if highs[i] > highest_high:
                    highest_high = highs[i]

            return highest_high, lowest_low
        
    def _calculate_distance_from_zone(self, zone: Zone, high: float, low: float) -> tuple[float, float]:
        """Calculates the distance of the high and low from zone in zone lengths."""

        range_from_zone_high = high - zone.high
        range_from_zone_low = zone.low - low

        zones_from_zone_upwards = round(range_from_zone_high / zone.range,2)
        zones_from_zone_downwards = round(range_from_zone_low / zone.range,2)

        return zones_from_zone_upwards, zones_from_zone_downwards
        
    def _calculate_distance_sma(self, zone: Zone, sma: float) -> float:
        """Calculate the distance of SMA at certain index, from the zone in zone lengths."""
        # If SMA is within the zone, return 0
        range_from_zone = None
        if zone.high > sma > zone.low:
            return 0.0

        # If the direction is the opposite, that we want in order to have proffitable trade,
        # return negative value.
        elif zone.low > sma:
            range_from_zone = zone.low - sma
            if zone.is_demand:
                range_from_zone *= (-1)

        elif sma > zone.high:
            range_from_zone = sma - zone.high
            if zone.is_supply:
                range_from_zone *= (-1)
        
        return round(range_from_zone / zone.range,2) if range_from_zone else 0.0


def print_sharp_wick():
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    all_results = []
    for year in years:
        data = get_data(type='parquet', year=year, timeframes=['1h'])
        msrs = Measurements(data, year)
        results = msrs.run()

        all_results.append(results)

    col_names = ['Year', 'Count', 'Fourth', 'Third', 'Second', 'First']
    table = PrettyTable()
    table.field_names = col_names

    for year, results in zip(years, all_results):
        table.add_row([year] + [round(v, 2) for v in results.values()])

    print(table)

def print_choppiness():
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

    field_names = [
        'Year',
        'FH - Downwards', 'FH - Upwards', 
        'SH - Downwards', 'SH - Upwards',
        'SMA 5 - changes', 'SMA 20 - changes', 
        'SMA 5 - highest', 'SMA 5 - lowest',
        'SMA 20 - highest','SMA 20 - lowest'
        ]

    table_winners = PrettyTable()
    table_winners.field_names = field_names

    table_losers = PrettyTable()
    table_losers.field_names = field_names

    for year in years:
        print(year)
        data = get_data(type='parquet', year=year, timeframes=['1h'])
        msrs = Measurements(data, year)
        winners, losers = msrs.run()

        table_winners.add_row([
            year,
            round(np.average([zone.indicators.first_half.highest_downward for zone in winners]),2),
            round(np.average([zone.indicators.first_half.highest_upward for zone in winners]),2),
            round(np.average([zone.indicators.second_half.highest_downward for zone in winners]),2),
            round(np.average([zone.indicators.second_half.highest_upward for zone in winners]),2),
            round(np.average([zone.indicators.sma_5.changes for zone in winners]),2),
            round(np.average([zone.indicators.sma_20.changes for zone in winners]),2),
            round(np.average([zone.indicators.sma_5.highest_throughout_indexes for zone in winners]),2),
            round(np.average([zone.indicators.sma_5.lowest_throughout_indexes for zone in winners]),2),
            round(np.average([zone.indicators.sma_20.highest_throughout_indexes for zone in winners]),2),
            round(np.average([zone.indicators.sma_20.lowest_throughout_indexes for zone in winners]),2)
        ])

        table_losers.add_row([
            year,
            round(np.average([zone.indicators.first_half.highest_downward for zone in losers]),2),
            round(np.average([zone.indicators.first_half.highest_upward for zone in losers]),2),
            round(np.average([zone.indicators.second_half.highest_downward for zone in losers]),2),
            round(np.average([zone.indicators.second_half.highest_upward for zone in losers]),2),
            round(np.average([zone.indicators.sma_5.changes for zone in losers]),2),
            round(np.average([zone.indicators.sma_20.changes for zone in losers]),2),
            round(np.average([zone.indicators.sma_5.highest_throughout_indexes for zone in losers]),2),
            round(np.average([zone.indicators.sma_5.lowest_throughout_indexes for zone in losers]),2),
            round(np.average([zone.indicators.sma_20.highest_throughout_indexes for zone in losers]),2),
            round(np.average([zone.indicators.sma_20.lowest_throughout_indexes for zone in losers]),2)
        ])

    print("WINNERS")
    print(table_winners)

    print("LOSERS")
    print(table_losers)



def main():
    print_choppiness()

if __name__ == "__main__":
    main()