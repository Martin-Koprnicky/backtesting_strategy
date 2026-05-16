"""
Run Backtest
============

Main entry point for running backtests on historical trading data.

Loops through years separately, so the memory doesn't get overloaded.
After year is loaded, it is checked for all zones by pattern detector.
Once zones in that year are detected, they are passed into trade executor, 
where zones are executed, separately, so they don't overlap.

Usage:
------
    python -m run
"""

import pandas as pd
import numpy as np
import time
import csv
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('MacOSX')
import logging
import shutil

from prettytable import PrettyTable
from typing import List
from pathlib import Path

from data.data_handlers import get_data
from backtesting.multiple_entries_liquidity_validation.pattern_detection import PatternDetector
from backtesting.multiple_entries_liquidity_validation.trade_execution import BacktestEngine
from backtesting.multiple_entries_liquidity_validation.config.settings import load_config
from backtesting.multiple_entries_liquidity_validation.visualizations.visualizer import BacktestVisualizer
from backtesting.multiple_entries_liquidity_validation.config.logging_config import get_logger
from backtesting.multiple_entries_liquidity_validation.db.db_handler import run_handler

logger = get_logger(level="INFO")

def run():
    """This is the button, you wanna press to play!"""
    logger.info("Backtesting run started.")

    # Load configuration for backtesting
    config = load_config("backtesting/multiple_entries_liquidity_validation/config/default_config.toml")
    logger.info("Configuration loaded successfuly")
    patterns = config.general.patterns
    years = config.general.years

    # Set up variables
    all_results = []
    all_zones = []
    data_current_year = None
    data_next_year = None
    hours_slice_year = 1000

    print("="*7*len(patterns) + "==")
    print(patterns)
    print("="*7*len(patterns) + "==")

    data = None

    executed_zones = []

    for year in years:
        logger.info(f"YEAR TESTED: {year}")
        # If it's not last year, merge with one month of data of next year
        # so we could execute positions, that were spotted after Christmass.
        if year != years[-1]:

            # If it's first year loads up data for this and year after
            if data_current_year is None:
                data_current_year = get_data(type='parquet', year=year, timeframes=['1h', '15m', '5m', '1s'])
                data_next_year = get_data(type='parquet', year=year+1, timeframes=['1h', '15m', '5m', '1s'])

            # Switch year after into current and loads up new one
            else:
                data_current_year = data_next_year
                data_next_year = get_data(type='parquet', year=year+1, timeframes=['1h', '15m', '5m', '1s'])

            slice_next_year = {}

            # Make one month data slice of next year
            for timeframe, data in data_next_year.items():
                if timeframe == '1h':
                    end_idx = hours_slice_year
                elif timeframe == '15m':
                    end_idx = hours_slice_year * 4
                elif timeframe == '5m':
                    end_idx = hours_slice_year * 4 * 3
                elif timeframe == '1m':
                    end_idx = hours_slice_year * 4 * 3 * 5
                elif timeframe == '1s':
                    end_idx = hours_slice_year * 4 * 3 * 5 * 60

                slice_next_year[f'{timeframe}'] = data.iloc[0:end_idx]

            data_plus_month = {}

            # Zip both years, so we could merge them together, 
            # one of them is items(), cause we need timeframe,
            # in order to store it properly
            for (timeframe ,first_year), plus_month in zip(data_current_year.items(), slice_next_year.values()):
                # Merge two dataframes together
                data_plus_month[f'{timeframe}'] = pd.concat([first_year, plus_month])

            # Pattern detector
            logger.info(f"Pattern detection is starting")
            detector = PatternDetector(config, data_current_year['1h'], data_plus_month['1h'])
            zones = detector.detect_patterns()

            # Position executor
            logger.info(f"Trade execution is starting")
            backtest_engine = BacktestEngine(zones, config, data_plus_month)
            results, exe_zones = backtest_engine.run()

        else:
            if data is None:
                data = get_data(type='parquet', year=year, timeframes=['1h', '15m', '5m', '1s'])
            else:
                data = data_next_year

            # Pattern detector
            logger.info(f"Pattern detection is starting")
            detector = PatternDetector(config, data['1h'])
            zones = detector.detect_patterns()

            # Position executor
            logger.info(f"Trade execution is starting")
            results, exe_zones = BacktestEngine(zones, config, data).run()

        
        for zone in exe_zones:
            zone.year = year
        
        executed_zones.extend(exe_zones)

        # Append results into all_results list, so we could print them nicely
        all_results.append(results)

        # Append zones into all_zones list, so we could save them into csv,
        # and make statistical report about what's good and what's bad.
        # We can even poke around with machine learning models.
        all_zones.append(exe_zones)

        if False:
            # Visualize the last year's executed zones
            last_data = data if year == years[-1] else data_plus_month
            BacktestVisualizer(config, last_data).plot_all(exe_zones, output_dir="backtesting/multiple_entries_liquidity_validation/visualizations/output", top_n='ALL', detail=True)

    # Print results with prettytable
    _print_results(all_results, years)

    # Save zones into csv file for ML purposes
    _save_zones_csv(executed_zones)

    # Save run into SQL database
    #run_handler(config, executed_zones)

def _print_results(all_results: List[dict], years: List[int]) -> None:
    """
    Print results from all years backtested with prettytable

    Args:
        all_results : Results from all backtested years
        years : List of backtested years
    """

    # Prepare column names for prettytable
    col_names = [
        "Year",
        "End. balance",
        "Fees",
        "E. zones",
        "Unexe. zones",
        "Unfin. zones",
        "Entries hit",
        "Avg entry hit",
        "Win rate",
        "Loss rate",
        "Avg win",
        "Avg loss",
        "H. win",
        "H. loss"
    ]

    table = PrettyTable()
    table.field_names = col_names

    # Zip years and results together, so we could merge them together into rows
    # Then add rows into pretty table
    for year, results in zip(years, all_results):
        table.add_row([year] + [round(v, 2) for v in results.values()])

    # Add also average row for entire backtesting
    df = pd.DataFrame(all_results)
    avg = df.mean()
    table.add_row(["AVG"] + [round(v, 2) for v in avg.values])

    print(table)

def _save_zones_csv(zones: list) -> None:
    """
    Saves zones for current year into csv file.

    Args:
        zones : List of executed zones for current year
    """
    with open('backtesting/multiple_entries_liquidity_validation/measure_zones.csv', mode='w', newline='') as file:
        fieldnames = [
            'year',
            'pnl',
            'zone_type',
            'pattern_type',
            'base_candle_count',
            'base_tightness_ratio',
            'before_candle_count',
            'before_strongest',
            'before_weakest',
            'before_average_with_strongest',
            'after_candle_count',
            'after_strongest',
            'after_weakest',
            'after_average_with_strongest',
            'liquidity_dip'
            ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if file.tell() == 0:
            writer.writeheader()

        for zone in zones:
            writer.writerow({
                'year': zone.year,
                'pnl': zone.stats.netto,
                'zone_type': zone.type.value,
                'pattern_type': zone.pattern.value,
                'base_candle_count': zone.base.candle_count,
                'base_tightness_ratio': zone.base.tightness_ratio,
                'before_candle_count': zone.movement_before.candle_count,
                'before_strongest': zone.movement_before.candle_scores.strongest,
                'before_weakest': zone.movement_before.candle_scores.weakest,
                'before_average_with_strongest': zone.movement_before.candle_scores.average_with_strongest,
                'after_candle_count': zone.movement_after.candle_count,
                'after_strongest': zone.movement_after.candle_scores.strongest,
                'after_weakest': zone.movement_after.candle_scores.weakest,
                'after_average_with_strongest': zone.movement_after.candle_scores.average_with_strongest,
                'liquidity_dip': zone.lq_validation.liquidity_dip
            })

def main():
    run()
    #add_to_csv()
    #print_capital_chart()

def add_to_csv() -> None:
    """
    Add columns into zones.csv
    
    Mainly for adding index and capital, for later usage.
    """

    shutil.copy('backtesting/multiple_entries_liquidity_validation/measure_zones.csv', 'backtesting/multiple_entries_liquidity_validation/zones.csv')
    df = pd.read_csv('backtesting/multiple_entries_liquidity_validation/zones.csv')

    df['index'] = [i for i in range(len(df))]
    df['capital'] = 1000 + df['pnl'].cumsum()

    print(df)
    df.to_csv('backtesting/multiple_entries_liquidity_validation/zones.csv', index=False)

def print_capital_chart() -> None:
    """
    Print capital growth chart.
    
    We can check out, how much our strategy gotten worse over the years.
    """

    # Make sure to import all neccessary libraries
    df = pd.read_csv('backtesting/multiple_entries_liquidity_validation/zones.csv')

    plt.scatter(x=df['index'], y=df['capital'], s=5)
    plt.xticks(range(0, len(df) + 1, 100))
    plt.xlabel('Trade #')
    plt.ylabel('Capital')
    plt.title('Capital Growth')
    plt.savefig('backtesting/multiple_entries_liquidity_validation/capital_growth.png', dpi=150)
    plt.close()

if __name__ == "__main__":
    main()


