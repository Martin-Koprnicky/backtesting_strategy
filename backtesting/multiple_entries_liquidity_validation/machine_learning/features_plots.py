import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from typing import Literal

def _divide_zones(df: pd.DataFrame) -> list[pd.DataFrame]:

    return  [
        df[(df['year'] <= 2023) & (df['profitable'] > 0)], 
        df[(df['year'] <= 2023) & (df['profitable'] <= 0)],
        df[(df['year'] > 2023) & (df['profitable'] > 0)],
        df[(df['year'] > 2023) & (df['profitable'] <= 0)]
    ]

def _plot_feature(values: list[float], labels: list[str], title: str) -> None:

    for val, lab in zip(values, labels):
        print(f"{lab} = {round(val,2)}")

    fig, ax = plt.subplots(figsize=(8,6))

    length = np.arange(0, len(values)) + 0.5

    ax.bar(length, values, color='#B2D7D0')
    ax.set_xticks(length)
    ax.set_xticklabels([label.replace('_', '\n') for label in labels], fontsize=12)
    ax.set_xlim(0, len(values))
    ax.set_title(f"{title}")
    fig.tight_layout()
    plt.show()

def _make_values_from_dfs(dfs: list[pd.DataFrame], column: str, agg_func: Literal['sum', 'count', 'mean', 'std'], pct: bool = False) -> list[float]:

    if pct:
        zones_before = sum([(df[df['year'] <= 2023][column]).count() for df in dfs])
        zones_after = sum([(df[df['year'] > 2023][column]).count() for df in dfs])

        values = []
        for df in dfs:
            if df['year'].iloc[0] <= 2023:
                values.append(((getattr(df[column], agg_func)()) / zones_before) * 100)
            elif df['year'].iloc[0] > 2023:
                values.append(((getattr(df[column], agg_func)()) / zones_after) * 100)

        return values

    return [getattr(df[column], agg_func)() for df in dfs]

def _get_labels(suffix: str = '') -> list[str]:

    base = ['winners_before', 'losers_before', 'winners_after', 'losers_after']
    return [f'{label}{suffix}' for label in base]
    
def plot_sma_distance_from_zone(df: pd.DataFrame, period: int) -> None:

    dfs = _divide_zones(df)

    values = _make_values_from_dfs(dfs, f'sma_{period}_distance_from_zone', 'std')
    labels = _get_labels('_std')

    title = f"SMA {period} - Distance from zone"

    _plot_feature(values, labels, title)

def plot_sma_direction(df: pd.DataFrame, period: int) -> None:

    dfs = _divide_zones(df)
    column = f'sma_{period}_direction'

    favourables = _make_values_from_dfs([df[df[column] == 1] for df in dfs], column, 'count')
    unfavourables = _make_values_from_dfs([df[df[column] == -1] for df in dfs], column, 'count')

    fav_labels = _get_labels('_fav_count')
    unfav_labels = _get_labels('_unfav_count')

    values = [*favourables, *unfavourables]
    labels = [*fav_labels, *unfav_labels]
    
    title = f"SMA {period} - Direction"

    _plot_feature(values, labels, title)

def plot_sma_direction_pct(df: pd.DataFrame, period: int) -> None:

    dfs = _divide_zones(df)
    column = f'sma_{period}_direction'

    favourables = _make_values_from_dfs([df[df[column] == 1] for df in dfs], column, 'count', pct=True)
    unfavourables = _make_values_from_dfs([df[df[column] == -1] for df in dfs], column, 'count', pct=True)

    fav_labels = _get_labels('_fav_count_pct')
    unfav_labels = _get_labels('_unfav_count_pct')

    values = [*favourables, *unfavourables]
    labels = [*fav_labels, *unfav_labels]
    
    title = f"SMA {period} - Direction percentage"

    _plot_feature(values, labels, title)


def plot_lower_sma_vs_higher_sma(df) -> None:

    dfs = _divide_zones(df)

    favs = _make_values_from_dfs(dfs, )