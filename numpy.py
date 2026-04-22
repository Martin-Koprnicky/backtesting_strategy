import pandas as pd
from typing import Literal, Optional, Union

def numpy_arrays(data: pd.DataFrame) -> dict:
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

def cut_numpy_arrays(start_index: int, end_index: int, np_arrays: dict) -> dict:
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


