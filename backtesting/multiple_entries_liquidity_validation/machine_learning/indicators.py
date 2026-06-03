import pandas as pd
import numpy as np

from typing import Literal

class IndicatorCalculator:
    def __init__(self):
        pass

    def sma(self, df: pd.DataFrame, period: int, ohlc: Literal['open', 'high', 'low', 'close'] = 'close') -> pd.DataFrame:
        """
        Calculation of SMA values on DataFrame close values.
        
        Args:
            df : Pandas DataFrame of OHLCV values
            period : Length of calculated period
            
        Returns:
            pandas.dataframe with new column of values
        """

        df[f'sma_{period}'] = df[f'{ohlc}'].rolling(period).mean()

        return df
    
    def distance_SMA_from_zone(self, df: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
        """
        Calculation of distance of SMA from zone in zone measurement..

        If SMA is three times more away from zone, as length of zone, then the value would be 3.

        Can be either positive or negative value, depends if the SMA is in our favour or not.

        Args:
            df : Pandas DataFrame of OHLCV values
            zones : Pandas DataFrame of zones

        Returns:
            pandas.dataframe of zones with new column of distance value
        """

        zones['validation_time'] = pd.to_datetime(zones['validation_time'])

        # Exctract only rows that we want from df, so we can match it with zones
        df_merged = pd.merge(df, zones, left_on=df.index, right_on='validation_time', how='inner')
        
        for column in ['close_time', 'open', 'high', 'low', 'close', 'volume_USDT']:
            df_merged = df_merged.drop(column, axis=1)
        
        conditions = [
            (df_merged['sma_20'] > df_merged['base_low']) & (df_merged['sma_20'] < df_merged['base_high']),
            df_merged['sma_20'] < df_merged['base_low'],
            df_merged['sma_20'] > df_merged['base_high']
        ]

        results = [
            0,
            round(((df_merged['base_low'] - df_merged['sma_20']) * np.where(df_merged['zone_type'] == 1, -1, 1)) / (df_merged['base_high'] - df_merged['base_low']), 2),
            round((df_merged['sma_20'] - df_merged['base_high']) * np.where(df_merged['zone_type'] == 0, -1, 1) / (df_merged['base_high'] - df_merged['base_low']), 2)
        ]

        df_merged['distance_sma_from_zone'] = np.select(conditions, results, default=0)

        return df_merged




