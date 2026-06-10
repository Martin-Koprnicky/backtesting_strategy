import pandas as pd
import numpy as np
import math

from typing import Literal, Optional, Union

class IndicatorCalculator:
    def __init__(self):
        pass


    # =============================================================================
    # SIMPLE MOVING AVERAGE
    # =============================================================================


    def sma(self, df: pd.DataFrame, period: int, ohlc: Literal['open', 'high', 'low', 'close'] = 'close', shift: int = 1) -> None:
        """
        Calculation of SMA values on DataFrame close values.
        
        Args:
            df : Pandas DataFrame of OHLCV values
            period : Length of calculated period
            
        Returns:
            pandas.dataframe with new column of values
        """

        df[f'sma_{period}'] = df[f'{ohlc}'].rolling(period).mean()
        df[f'sma_{period}_shift_by_{shift}'] = df[f'sma_{period}'].shift(shift)

    def merge_zones_with_indi_vals(self, indi_vals_df: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
        """
        Merge calculated indicator values with zones.

        Args:
            indi_vals_df : Calculated indicator values
            zones : measure_zones.csv file

        Return:
            inner merged version of arguments by validation index
        """

        zones['validation_time'] = pd.to_datetime(zones['validation_time'])

        # Exctract only rows that we want from df, so we can match it with zones

        zones = pd.merge(indi_vals_df, zones, left_on=indi_vals_df.index, right_on='validation_time', how='inner')
        
        for column in ['close_time', 'open', 'high', 'low', 'close', 'volume_USDT']:
            zones = zones.drop(column, axis=1)

        return zones

    def distance_SMA_from_zone(self, zones: pd.DataFrame, periods: list[int]) -> None:
        """
        Calculation of distance of SMA from zone in zone measurement..

        If SMA is three times more away from zone, as length of zone, then the value would be 3.

        Can be either positive or negative value, depends if the SMA is in our favour or not.

        Args:
            zones : zones with indicator values at validation timestamp
            periods : indicator periods, in case of SMA or EMA 
        """
        
        for period in periods:
            conditions = [
                (zones[f'sma_{period}'] > zones['base_low']) & (zones[f'sma_{period}'] < zones['base_high']),
                zones[f'sma_{period}'] < zones['base_low'],
                zones[f'sma_{period}'] > zones['base_high']
            ]

            results = [
                0,
                round(((zones['base_low'] - zones[f'sma_{period}']) * np.where(zones['zone_type'] == 1, -1, 1)) / (zones['base_high'] - zones['base_low']), 2),
                round((zones[f'sma_{period}'] - zones['base_high']) * np.where(zones['zone_type'] == 0, -1, 1) / (zones['base_high'] - zones['base_low']), 2)
            ]

            zones[f'sma_{period}_distance_from_zone'] = np.select(conditions, results, default=0)

    def direction_of_SMA_at_lq_validation(self, zones: pd.DataFrame, periods: list[int], shift: int = 1) -> None:
        """
        Calculation of direction of SMA at lq validation point..

        Args:
            zones : zones with indicator values at validation timestamp
            periods : indicator periods, in case of SMA or EMA 
        """

        for period in periods:
            column = f'sma_{period}_direction'

            zones[column] = np.where(zones[f'sma_{period}_shift_by_{shift}'] < zones[f'sma_{period}'], 1, -1)
            zones[column] = np.where(zones['zone_type'] == 1, zones[column]*1, zones[column]*(-1))

    def lower_sma_vs_higher_sma(self, zones: pd.DataFrame, periods: list[int]) -> None:
        """
        Calculation of relationship between two SMAs.

        Args:
            zones : zones with indicator values at validation timestamp
            periods : indicator periods, in case of SMA or EMA  
        """
        higher_period = max(periods)
        lower_period = min(periods)

        column = f'sma_{lower_period}_vs_sma_{higher_period}'

        zones[column] = np.where(zones[f'sma_{lower_period}'] > zones[f'sma_{higher_period}'], 1, -1)
        zones[column] = np.where(zones['zone_type'] == 1, zones[column]*1, zones[column]*(-1))
        

    # =============================================================================
    # MOMENTUM MAGNITUDE OF SMA
    # =============================================================================


    def momentum_magnitude_of_lower_sma_and_higher_sma(self, zones: pd.DataFrame, periods: list[int], shift: int = 1) -> None:
        """
        Calculation of momentum magnitude of SMAs during zone creation.

        Relation between two SMAs is one method above,
        now we focus on momentum of those two SMAs. If the gap between them is accelerating or fading.
        
        Args:
            zones : zones with indicator values at validation timestamp
            periods: indicator periods, in case of SMA or EMA
        """

        zone_range = zones['base_high'] - zones['base_low']

        column_now = 'momentum_magnitude_gap'
        column_before = f'momentum_magnitude_gap_shift_by_{shift}'
        
        zones[column_now] = (zones[f'sma_{min(periods)}'] - zones[f'sma_{max(periods)}']) / zone_range
        zones[column_now] = np.where(zones['zone_type'] == 1, zones[column_now]*1, zones[column_now]*(-1))

        zones[column_before] = (zones[f'sma_{min(periods)}_shift_by_{shift}'] - zones[f'sma_{max(periods)}_shift_by_{shift}']) / zone_range
        zones[column_before] = np.where(zones['zone_type'] == 1, zones[column_before]*1, zones[column_before]*(-1))

        zones[f'momentum_magnitude_diff_shift_by_{shift}'] = zones[column_now] - zones[column_before]

