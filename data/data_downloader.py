"""
Data Downloader
===============

This code downloads data from exchanges through Api keys.
Downloader has multiple methods, each for different timeframe.
Data are downloaded into csv, so they can be checked if they 
aren't corrupted. 

Usage:
------
    from data_downloader import get_data_1h

    # In variable list, years, sets years, you wanna download
    # Within each method are filepaths, that needs to be adjusted
    get_data_1h()

"""

import time
import pandas as pd
import csv

from binance.client import Client
from enum import Enum
from api_handler import load_api_holder


MONTHS = [
    ("Jan", "Feb"), ("Feb", "Mar"), ("Mar", "Apr"), ("Apr", "May"),
    ("May", "Jun"), ("Jun", "Jul"), ("Jul", "Aug"), ("Aug", "Sep"),
    ("Sep", "Oct"), ("Oct", "Nov"), ("Nov", "Dec"), ("Dec", "Jan")
]
YEARS = [2025]

class Interval(Enum):
    """Kline intervals for getting data from binance."""
    H1 = Client.KLINE_INTERVAL_1HOUR
    M15 = Client.KLINE_INTERVAL_15MINUTE
    M5 = Client.KLINE_INTERVAL_5MINUTE
    M1 = Client.KLINE_INTERVAL_1MINUTE
    S1 = Client.KLINE_INTERVAL_1SECOND


def _get_api_key_and_secret():
    holder = load_api_holder()
    return holder.binance.real._1.api_key, holder.binance.real._1.api_secret

def _get_data_from_binance(interval: Interval, starting_datetime: str, ending_datetime: str):
    api_key, api_secret = _get_api_key_and_secret()
    if not api_key or not api_secret:
        raise ValueError("API key and API secret are required to get data from Binance")
    
    client = Client(api_key=api_key, api_secret=api_secret)

    try:
        klines = client.get_historical_klines(
            symbol="BTCUSDT",
            interval=interval,
            start_str=starting_datetime,
            end_str=ending_datetime,
            limit=1000)
        
        return klines
    except Exception as exception:
        print(f"Error getting data from Binance: {exception}.")
        return None

def get_data_1h():
    for year in YEARS:
        year_data = []
        for start_month, end_month in MONTHS:
            
            end_year = year if end_month != "Jan" else year + 1
            
            starting_dat = f"1 {start_month}, {year}"
            ending_dat = f"1 {end_month}, {end_year}"

            print(f"Downloading 1H data: {starting_dat} - {ending_dat}")

            raw_data = _get_data_from_binance(
                interval=Interval.H1,
                starting_datetime=starting_dat,
                ending_datetime=ending_dat
            )

            if raw_data:
                year_data.extend(raw_data)

        filename = f'downloaded_data_unclean/1h/btc_1h_{year}.csv'
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(year_data)

        df = pd.read_csv(filename, names=[
            'open_time', 'open', 'high', 'low', 'close', 'volume_BTC', 'close_time', 'volume_USDT', 'number_of_trades', 'taker_buy_base_asset_volume_BTC', 'taker_buy_quote_asset_volume_USDT', 'ignore'
        ])

        df_clean = df.drop_duplicates(subset=['open_time'])

        df_clean.to_csv(f'csv_data/1h/btc_1h_{year}_clean.csv', index=False)
        print(f"Saving 1H data: {starting_dat} - {ending_dat}")

def get_data_15m():

    for year in YEARS:
        year_data = []
        for start_month, end_month in MONTHS:
            try:
                end_year = year if end_month != "Jan" else year + 1

                first_quarter_starting_dat = f"1 {start_month}, {year}"
                first_quarter_ending_dat = f"8 {start_month}, {year}"
                second_quarter_starting_dat = f"8 {start_month}, {year}"
                second_quarter_ending_dat = f"16 {start_month}, {year}"
                third_quarter_starting_dat = f"16 {start_month}, {year}"
                third_quarter_ending_dat = f"24 {start_month}, {year}"
                last_quarter_starting_dat = f"24 {start_month}, {year}"
                last_quarter_ending_dat = f"1 {end_month}, {end_year}"

                quarters = [
                    (first_quarter_starting_dat, first_quarter_ending_dat),
                    (second_quarter_starting_dat, second_quarter_ending_dat),
                    (third_quarter_starting_dat, third_quarter_ending_dat),
                    (last_quarter_starting_dat, last_quarter_ending_dat)
                ]

                for starting_date, ending_date in quarters:

                    print(f"Downloading 15min data: {starting_date} - {ending_date}")

                    raw_data = _get_data_from_binance(
                        interval=Interval.M15,
                        starting_datetime=starting_date,
                        ending_datetime=ending_date
                    )

                    if raw_data:
                        year_data.extend(raw_data)

            except ValueError as e:
                print(f"Date error for {starting_date}: {e}")
                continue
            except ConnectionError as e:
                print(f"Network error: {e}")
                time.sleep(30)  # Wait and continue
                continue
            except Exception as e:
                print(f"Unexpected error: {e}")
                continue

        filename = f'downloaded_data_unclean/15m/btc_15m_{year}.csv'
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(year_data)

        df = pd.read_csv(filename, names=['open_time', 'open', 'high', 'low', 'close', 'volume_BTC', 'close_time', 'volume_USDT', 'number_of_trades', 'taker_buy_base_asset_volume_BTC', 'taker_buy_quote_asset_volume_USDT', 'ignore'])
        df_clean = df.drop_duplicates(subset=['open_time'])
        df_clean.to_csv(f'csv_data/15m/btc_15m_{year}_clean.csv', index=False)
        print(f"Saving 15m data: {[quarters[0][0]]} - {ending_date}")

def get_data_5m():

    for year in YEARS:
        year_data = []
        for start_month, end_month in MONTHS:
            try:
                end_year = year if end_month != "Jan" else year + 1

                if start_month == "Feb":
                    days = [
                        (f"1 {start_month}, {year}", f"3 {start_month}, {year}"),
                        (f"3 {start_month}, {year}", f"6 {start_month}, {year}"),
                        (f"6 {start_month}, {year}", f"9 {start_month}, {year}"),
                        (f"9 {start_month}, {year}", f"12 {start_month}, {year}"),
                        (f"12 {start_month}, {year}", f"15 {start_month}, {year}"),
                        (f"15 {start_month}, {year}", f"18 {start_month}, {year}"),
                        (f"18 {start_month}, {year}", f"21 {start_month}, {year}"),
                        (f"21 {start_month}, {year}", f"24 {start_month}, {year}"),
                        (f"24 {start_month}, {year}", f"27 {start_month}, {year}"),
                        (f"27 {start_month}, {year}", f"1 {end_month}, {end_year}"),
                    ]

                else:
                    days = [
                        (f"1 {start_month}, {year}", f"3 {start_month}, {year}"),
                        (f"3 {start_month}, {year}", f"6 {start_month}, {year}"),
                        (f"6 {start_month}, {year}", f"9 {start_month}, {year}"),
                        (f"9 {start_month}, {year}", f"12 {start_month}, {year}"),
                        (f"12 {start_month}, {year}", f"15 {start_month}, {year}"),
                        (f"15 {start_month}, {year}", f"18 {start_month}, {year}"),
                        (f"18 {start_month}, {year}", f"21 {start_month}, {year}"),
                        (f"21 {start_month}, {year}", f"24 {start_month}, {year}"),
                        (f"24 {start_month}, {year}", f"27 {start_month}, {year}"),
                        (f"27 {start_month}, {year}", f"29 {start_month}, {year}"),
                        (f"29 {start_month}, {year}", f"1 {end_month}, {end_year}")
                    ]

                for starting_date, ending_date in days:

                    print(f"Downloading 5min data: {starting_date} - {ending_date}")

                    raw_data = _get_data_from_binance(
                        interval=Interval.M5,
                        starting_datetime=starting_date,
                        ending_datetime=ending_date
                    )

                    if raw_data:
                        year_data.extend(raw_data)

            except ValueError as e:
                print(f"Date error for {starting_date}: {e}")
                continue
            except ConnectionError as e:
                print(f"Network error: {e}")
                time.sleep(30)  # Wait and continue
                continue
            except Exception as e:
                print(f"Unexpected error: {e}")
                continue

        filename = f'downloaded_data_unclean/5m/btc_5m_{year}.csv'
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(year_data)

        df = pd.read_csv(filename, names=['open_time', 'open', 'high', 'low', 'close', 'volume_BTC', 'close_time', 'volume_USDT', 'number_of_trades', 'taker_buy_base_asset_volume_BTC', 'taker_buy_quote_asset_volume_USDT', 'ignore'])
        df_clean = df.drop_duplicates(subset=['open_time'])
        df_clean.to_csv(f'csv_data/5m/btc_5m_{year}_clean.csv', index=False)
        print(f"Saving 5min data: {starting_date} - {ending_date}")

def get_data_1m():

    # 2 chunks per day: 00:00-12:00 and 12:00-00:00 (720 candles each, within 1000 limit)
    chunks = [
        ("00:00:00", "12:00:00", False),
        ("12:00:00", "00:00:00", True),   # end_time is on next day
    ]

    for year in YEARS:
        print(f"\n=== DOWNLOADING {year} ===")
        year_data = []

        if year in [2020, 2024, 2028]:
            all_months = [
                ("Jan", 31), ("Feb", 29), ("Mar", 31), ("Apr", 30),
                ("May", 31), ("Jun", 30), ("Jul", 31), ("Aug", 31),
                ("Sep", 30), ("Oct", 31), ("Nov", 30), ("Dec", 31)
            ]
        else:
            all_months = [
                ("Jan", 31), ("Feb", 28), ("Mar", 31), ("Apr", 30),
                ("May", 31), ("Jun", 30), ("Jul", 31), ("Aug", 31),
                ("Sep", 30), ("Oct", 31), ("Nov", 30), ("Dec", 31)
            ]

        for month_name, month_days in all_months:
            print(f"{month_name} {year}...")

            for day in range(1, month_days + 1):
                print(f"  Downloading {month_name} {day}/{month_days}...")

                for start_time, end_time, next_day in chunks:
                    try:
                        starting_date = f"{day} {month_name}, {year} {start_time}"

                        if next_day:
                            if day < month_days:
                                ending_date = f"{day + 1} {month_name}, {year} {end_time}"
                            else:
                                # Last day of month — roll over to next month
                                current_idx = [m[0] for m in all_months].index(month_name)
                                if current_idx < 11:
                                    next_month = all_months[current_idx + 1][0]
                                    ending_date = f"1 {next_month}, {year} {end_time}"
                                else:
                                    ending_date = f"1 Jan, {year + 1} {end_time}"
                        else:
                            ending_date = f"{day} {month_name}, {year} {end_time}"

                        raw_data = _get_data_from_binance(
                            interval=Interval.M1,
                            starting_datetime=starting_date,
                            ending_datetime=ending_date
                        )

                        if raw_data:
                            year_data.extend(raw_data)

                        time.sleep(0.2)

                    except ValueError as e:
                        print(f"    Date error: {starting_date} - {e}")
                        continue
                    except ConnectionError as e:
                        print(f"    Network error: {e}")
                        time.sleep(30)
                        continue
                    except Exception as e:
                        print(f"    Unexpected error: {starting_date} - {e}")
                        continue

            print(f"  {month_name} done. Total candles so far: {len(year_data):,}")

        filename = f'downloaded_data_unclean/1m/btc_1m_{year}.csv'
        print(f"\nSaving {len(year_data):,} candles to {filename}...")

        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(year_data)

        df = pd.read_csv(filename, names=[
            'open_time', 'open', 'high', 'low', 'close', 'volume_BTC',
            'close_time', 'volume_USDT', 'number_of_trades',
            'taker_buy_base_asset_volume_BTC', 'taker_buy_quote_asset_volume_USDT', 'ignore'
        ])
        df_clean = df.drop_duplicates(subset=['open_time'])
        clean_filename = f'csv_data/1m/btc_1m_{year}_clean.csv'
        df_clean.to_csv(clean_filename, index=False)

        print(f"✓ YEAR {year} COMPLETED! {len(df_clean):,} candles → {clean_filename}")

def get_data_1s():
    """Download 1-second data for June 2025 for testing"""

    for year in YEARS:
        year_data = []

        if year in [2016, 2020, 2024, 2028]:
            all_months = [
                ("Jan", 31), ("Feb", 29), ("Mar", 31), ("Apr", 30),
                ("May", 31), ("Jun", 30), ("Jul", 31), ("Aug", 31),
                ("Sep", 30), ("Oct", 31), ("Nov", 30), ("Dec", 31)
            ]
        else:
            all_months = [
                ("Jan", 31), ("Feb", 28), ("Mar", 31), ("Apr", 30),
                ("May", 31), ("Jun", 30), ("Jul", 31), ("Aug", 31),
                ("Sep", 30), ("Oct", 31), ("Nov", 30), ("Dec", 31)
            ]
        
        # 15-minute chunks: 0:00, 0:15, 0:30, 0:45 each hour
        chunks = []
        for hour in range(24):
            for quarter in [0, 15, 30, 45]:
                start_time = f"{hour:02d}:{quarter:02d}:00"
                
                # Calculate end time (15 minutes later)
                end_quarter = quarter + 15
                end_hour = hour
                if end_quarter >= 60:
                    end_quarter = 0
                    end_hour += 1
                if end_hour >= 24:
                    end_hour = 0
                    
                end_time = f"{end_hour:02d}:{end_quarter:02d}:00"
                chunks.append((start_time, end_time, end_hour < hour))  # next_day flag
        
        print(f"Starting download of June 2025 1-second data...")
        print(f"Total chunks per day: {len(chunks)}")
        
        for month_name, days_in_month in all_months:
            print(f"\n=== DOWNLOADING {month_name.upper()} {year} ===")
            
            for day in range(1, days_in_month + 1):
                print(f"Downloading {month_name} {day}/{days_in_month}...")
                
                for start_time, end_time, next_day in chunks:
                    try:
                        starting_date = f"{day} {month_name}, {year} {start_time}"
                        
                        if next_day and day < days_in_month:
                            ending_date = f"{day + 1} {month_name}, {year} {end_time}"
                        elif next_day and day == days_in_month:
                            # Handle month rollover
                            current_month_idx = [m[0] for m in all_months].index(month_name)
                            if current_month_idx < 11:  # Not December
                                next_month = all_months[current_month_idx + 1][0]
                                ending_date = f"1 {next_month}, {year} {end_time}"
                            else:  # December -> January next year
                                ending_date = f"1 Jan, {year + 1} {end_time}"
                        else:
                            ending_date = f"{day} {month_name}, {year} {end_time}"
                        
                        raw_data = _get_data_from_binance(
                            interval=Interval.S1,
                            starting_datetime=starting_date,
                            ending_datetime=ending_date
                        )
                        
                        if raw_data:
                            year_data.extend(raw_data)
                        
                    except Exception as e:
                        print(f"  ✗ Error: {starting_date} - {e}")
                        time.sleep(2)
                        continue
            
            print(f"✓ {month_name} completed. Total candles so far: {len(year_data):,}")
        
        # Save the full year data
        filename = f'downloaded_data_unclean/1s/btc_1s_{year}.csv'
        print(f"\nSaving {len(year_data):,} candles to {filename}...")
        
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(year_data)
        
        # Clean duplicates
        df = pd.read_csv(filename, names=[
            'open_time', 'open', 'high', 'low', 'close', 'volume_BTC', 
            'close_time', 'volume_USDT', 'number_of_trades', 
            'taker_buy_base_asset_volume_BTC', 'taker_buy_quote_asset_volume_USDT', 'ignore'
        ])
        
        df_clean = df.drop_duplicates(subset=['open_time'])
        clean_filename = f'csv_data/1s/btc_1s_{year}_clean.csv'
        df_clean.to_csv(clean_filename, index=False)
        
        print(f"\n✓ YEAR {year} COMPLETED!")
        print(f"Clean data saved to {clean_filename}")
        print(f"Total candles: {len(df_clean):,}")
        print(f"Expected candles for {year}: ~{366 * 24 * 60 * 60:,} (leap year)")

def main():
    get_data_1s()
    
if __name__ == "__main__":
    main()