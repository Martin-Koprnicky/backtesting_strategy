"""
Data Handler
============

Loads data from storage, restruct them into pandas DataFrame.
File paths within all methods needs to be adjusted.

Usage:
------
    from data_handlers import get_data

    years = [2023, 2024]
    timeframes = ['1h', '5m', '1s']
    data = get_data(type='parquet', year=years, timeframes=timeframes)

"""

import pandas as pd

from binance.client import Client
from typing import Literal


def get_data(type: Literal['parquet', 'csv'], year: int, timeframes: list[str]) -> dict:
    """
    Load up data directly from storage.

    Args:
        type : Type of data, parquet or csv
        year : Current year to load up
        timeframes : List of timeframes to use

    Returns:
        dict : {'1h': pd.DataFrame, ...}
    
    """
    result = {}
    for tf in timeframes:
        if type == 'parquet':
            handler = ParquetDataHandler(tf, year)
        elif type == 'csv':
            handler = CSVDataHandler(tf, year)

        result[tf] = handler._get_data()
    return result

class CSVDataHandler:
    def __init__(self, timeframe, year):
        self.timeframe = timeframe
        self.year = year
        self.file_path = f'data/csv_data/{timeframe}/btc_{timeframe}_{year}_clean.csv'

        self.raw_data = None
        self.processed_data = None
    
    def _load_csv(self):
        """Load CSV data."""
        try:
            self.raw_data = pd.read_csv(self.file_path)
            return self.raw_data
        
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")
            return None
        except Exception as e:
            print(f"Error loading file: {e}")
            return None
        
    def _process_data(self):
        """Process csv data into pd.DataFrame."""
        if self.raw_data is None:
            print("No data loaded. Call load_csv() first.")
            return None
        
        try:
            data_frame = self.raw_data.copy()
            
            data_frame['open_time'] = pd.to_datetime(data_frame['open_time'], unit = 'ms')
            data_frame['close_time'] = pd.to_datetime(data_frame['close_time'], unit = 'ms')

            for col in ['open', 'high', 'low', 'close', 'volume_USDT']:
                data_frame[col] = data_frame[col].astype(float)
            
            usable_list = data_frame [['open_time', 'close_time', 'open', 'high', 'low', 'close', 'volume_USDT']]
            usable_list.set_index('open_time', inplace = True)

            self.processed_data = usable_list
            return self.processed_data
            
        except Exception as e:
            print(f"Error processing data: {e}")
            return None
    
    def _get_data(self):
        if self.processed_data is None:
            if self.raw_data is None:
                self._load_csv()
            return self._process_data()
        return self.processed_data

class ParquetDataHandler:
    def __init__(self, timeframe, year):
        self.timeframe = timeframe
        self.year = year
        self.file_path = f'data/parquet_data/{timeframe}/btc_{timeframe}_{year}_clean.parquet'

        self.raw_data = None
        self.processed_data = None

    def _load_parquet(self):
        """Load raw unreadable parquet data."""
        try:
            self.raw_data = pd.read_parquet(self.file_path)
            return self.raw_data
        except FileNotFoundError:
            print(f"File not found error, file path: {self.file_path}")
            return None
        except Exception as e:
            print(f"Error loading file: {e}")
            return None
    
    def _process_data(self):
        """Process loaded data into pd.DataFrame."""
        if self.raw_data is None:
            print("No data loaded, call load_parquet_data() first.")
            return None
        
        try:
            data_frame = self.raw_data.copy()
            
            if data_frame.index.name == 'open_time':
                data_frame = data_frame.reset_index()
            
            if 'open_time' in data_frame.columns and not pd.api.types.is_datetime64_any_dtype(data_frame['open_time']):
                data_frame['open_time'] = pd.to_datetime(data_frame['open_time'], unit='ms')
            if 'close_time' in data_frame.columns and not pd.api.types.is_datetime64_any_dtype(data_frame['close_time']):
                data_frame['close_time'] = pd.to_datetime(data_frame['close_time'], unit='ms')
            
            for col in ['open', 'high', 'low', 'close', 'volume_USDT']:
                if col in data_frame.columns:
                    data_frame[col] = data_frame[col].astype(float)
            
            usable_list = data_frame[['open_time', 'close_time', 'open', 'high', 'low', 'close', 'volume_USDT']]
            usable_list.set_index('open_time', inplace=True)
            
            self.processed_data = usable_list
            return self.processed_data
            
        except Exception as e:
            print(f"Error processing data: {e}")
            return None
    
    def _get_data(self):
        if self.processed_data is None:
            if self.raw_data is None:
                self._load_parquet()
            return self._process_data()
        return self.processed_data



