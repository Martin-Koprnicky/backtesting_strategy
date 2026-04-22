"""
Data Convertor
==============

File converts single or multiple csv files into parquet.
Parquet files are faster for usage, smaller to store them,
and smaller for loading into memory.

Usage:
------
    from data_convertor import run_convertor

    # Converts data from csv to parquet
    csv_path = ""
    parquet_path = ""

    run_convertor(csv_path, parquet_path)
"""
import pandas as pd
import os
from pathlib import Path
import time

from data_handlers import CSVDataHandler


def _convert_csv_to_parquet(csv_path, parquet_path):
    """Convert a single CSV file to Parquet format with optimized settings"""
    print(f"Converting {csv_path}...")
    start_time = time.perf_counter()
    
    try:
        # Read CSV with optimized settings
        df = pd.read_csv(csv_path, 
                         engine='c',
                         dtype={
                             'open': 'float32', 
                             'high': 'float32', 
                             'low': 'float32', 
                             'close': 'float32',
                             'volume_USDT': 'float32',
                             'volume_BTC': 'float32',
                             'number_of_trades': 'int32',
                             'taker_buy_base_asset_volume_BTC': 'float32',
                             'taker_buy_quote_asset_volume_USDT': 'float32'
                         })
        
        # Convert timestamps to datetime if they exist
        if 'open_time' in df.columns:
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        if 'close_time' in df.columns:
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # Create output directory if it doesn't exist
        Path(parquet_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save as Parquet with compression
        df.to_parquet(parquet_path, 
                      engine='pyarrow', 
                      compression='snappy',
                      index=False)
        
        end_time = time.perf_counter()
        file_size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
        print(f"✓ Saved to {parquet_path} ({file_size_mb:.1f}MB) in {end_time - start_time:.2f}s")
        
        return True
        
    except FileNotFoundError:
        print(f"✗ File not found: {csv_path}")
        return False
    except Exception as e:
        print(f"✗ Error converting {csv_path}: {e}")
        return False


def run_convertor():
    """Convert all CSV files to Parquet format"""
    # Configuration
    timeframes = ['1m']
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    
    # Base paths
    csv_base_path = 'csv_data'
    parquet_base_path = 'parquet_data'
    
    total_conversions = 0
    successful_conversions = 0
    
    print("Starting CSV to Parquet conversion...")
    print("=" * 50)
    
    for timeframe in timeframes:
        print(f"\nProcessing {timeframe} timeframe:")
        print("-" * 30)
        
        for year in years:
            csv_file = f'{csv_base_path}/{timeframe}/btc_{timeframe}_{year}_clean.csv'
            parquet_file = f'{parquet_base_path}/{timeframe}/btc_{timeframe}_{year}_clean.parquet'
            
            total_conversions += 1
            
            if os.path.exists(csv_file):
                success = _convert_csv_to_parquet(csv_file, parquet_file)
                if success:
                    successful_conversions += 1
            else:
                print(f"✗ CSV file not found: {csv_file}")
    
    print("\n" + "=" * 50)
    print(f"Conversion complete: {successful_conversions}/{total_conversions} files converted successfully")
    
    # Test loading speed comparison
    if successful_conversions > 0:
        print("\nTesting load speed comparison...")
        test_speed_comparison()


def test_speed_comparison():
    """Test the speed difference between CSV and Parquet loading"""
    
    # Find a file to test (preferably 1sec data for meaningful comparison)
    test_timeframe = '1h'
    test_year = 2020
    
    csv_file = f'data/csv_data/{test_timeframe}/btc_{test_timeframe}_{test_year}_clean.csv'
    parquet_file = f'data/parquet_data/{test_timeframe}/btc_{test_timeframe}_{test_year}_clean.parquet'
    
    if os.path.exists(csv_file) and os.path.exists(parquet_file):
        
        # Test CSV loading
        print(f"Testing CSV load speed for {test_timeframe} {test_year}...")
        start_csv = time.perf_counter()
        df_csv = pd.read_csv(csv_file)
        end_csv = time.perf_counter()
        csv_time = end_csv - start_csv
        
        # Test Parquet loading
        print(f"Testing Parquet load speed for {test_timeframe} {test_year}...")
        start_parquet = time.perf_counter()
        df_parquet = pd.read_parquet(parquet_file)
        end_parquet = time.perf_counter()
        parquet_time = end_parquet - start_parquet
        
        # Results
        speedup = csv_time / parquet_time if parquet_time > 0 else 0
        print(f"\nSpeed Comparison Results:")
        print(f"CSV loading time:     {csv_time:.2f} seconds")
        print(f"Parquet loading time: {parquet_time:.2f} seconds")
        print(f"Speedup factor:       {speedup:.1f}x faster")
        print(f"Data shape:           {df_parquet.shape}")
        
    else:
        print("Cannot run speed test - test files not found")


def fix_corrupted_data():
    timeframes = ['1h', '15m', '5m', '1s']
    years = [2025]

    for timeframe in timeframes:
        for year in years:
            print(f"Regenerating {timeframe} data for {year}...")
            
            # Load from working CSV
            csv_handler = CSVDataHandler(timeframe, year)
            csv_handler.load_csv()
            clean_data = csv_handler.get_data()
            
            # Verify no corruption
            print(f"Candles: {len(clean_data)}, NaN count: {clean_data.isna().sum().sum()}")
            
            # Save fresh parquet
            parquet_path = f'data/parquet_data/{timeframe}/btc_{timeframe}_{year}_clean.parquet'
            clean_data.to_parquet(parquet_path, compression='snappy')
            
            print(f"Fixed {timeframe} {year} ✓")


def data_shape():
    timeframes = ['1h', '15m', '5m', '1s']
    years = [2025]

    for timeframe in timeframes:
        for year in years:
            data = pd.read_parquet(f'parquet_data/{timeframe}/btc_{timeframe}_{year}_clean.parquet')
            data.isna().any()
            if data.isna().values.any():
                print(f"Is Na")
            print(data.shape)
            print(data.head())

def main():
    run_convertor()

if __name__ == "__main__":
    main()