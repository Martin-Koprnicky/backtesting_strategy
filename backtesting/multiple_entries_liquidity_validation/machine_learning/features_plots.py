import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from typing import Literal

# =============================================================================
# CORE PLOT METHODS
# =============================================================================


def _divide_zones(df: pd.DataFrame) -> list[pd.DataFrame]:

    return  [
        df[(df['year'] <= 2023) & (df['profitable'] > 0)], 
        df[(df['year'] <= 2023) & (df['profitable'] <= 0)],
        df[(df['year'] > 2023) & (df['profitable'] > 0)],
        df[(df['year'] > 2023) & (df['profitable'] <= 0)]
    ]

def _plot_feature(values: list[float], labels: list[str], title: str, pct: bool = False) -> None:

    for val, lab in zip(values, labels):
        print(f"{lab} = {round(val,2)}%" if pct else f"{lab} = {round(val,2)}")

    fig, ax = plt.subplots(figsize=(8,6))

    length = np.arange(0, len(values)) + 0.5

    ax.bar(length, values, color='#B2D7D0')
    ax.set_xticks(length)
    ax.set_xticklabels([label.replace('_', '\n') for label in labels], fontsize=12)
    ax.set_xlim(0, len(values))
    ax.set_title(f"{title}")
    fig.tight_layout()
    plt.show()

def _make_values_from_dfs(dfs: list[pd.DataFrame], column: str, agg_func: Literal['sum', 'count', 'mean', 'std'], pct: bool = False, raw_df: pd.DataFrame = None) -> list[float]:

    if pct:
        zones_before = (raw_df[raw_df['year'] <= 2023][column]).count()
        zones_after = (raw_df[raw_df['year'] > 2023][column]).count()

        values = []
        for df in dfs:
            if df['year'].iloc[0] <= 2023:
                values.append(((getattr(df[column], agg_func)()) / zones_before) * 100)
            elif df['year'].iloc[0] > 2023:
                values.append(((getattr(df[column], agg_func)()) / zones_after) * 100)

        return values

    return [getattr(df[column], agg_func)() for df in dfs]

def _get_labels(suffix: str = '') -> list[str]:

    return [f'{label}{suffix}' for label in ['winners_before', 'losers_before', 'winners_after', 'losers_after']]


# =============================================================================
# SIMPLE MOVING AVERAGE
# =============================================================================


def plot_sma_distance_from_zone(df: pd.DataFrame, period: int) -> None:

    print(f"\nSMA {period}, distance from zone\n", "-"*30, sep="")

    dfs = _divide_zones(df)

    values = _make_values_from_dfs(dfs, f'sma_{period}_distance_from_zone', 'std')
    labels = _get_labels('_std')

    title = f"SMA {period} - Distance from zone"

    _plot_feature(values, labels, title)

def plot_sma_direction(df: pd.DataFrame, period: int) -> None:

    print(f"\nSMA {period}, direction with shift\n", "-"*30, sep="")

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

    print(f"\nSMA {period}, direction with shift, by percentages\n", "-"*30, sep="")

    dfs = _divide_zones(df)
    column = f'sma_{period}_direction'

    favourables = _make_values_from_dfs([df[df[column] == 1] for df in dfs], column, 'count', pct=True, raw_df=df)
    unfavourables = _make_values_from_dfs([df[df[column] == -1] for df in dfs], column, 'count', pct=True, raw_df=df)

    fav_labels = _get_labels('_fav_count_pct')
    unfav_labels = _get_labels('_unfav_count_pct')

    values = [*favourables, *unfavourables]
    labels = [*fav_labels, *unfav_labels]
    
    title = f"SMA {period} - Direction percentage"

    _plot_feature(values, labels, title, pct=True)

def plot_lower_sma_vs_higher_sma(df: pd.DataFrame, periods: list[int]) -> None:

    print(f"\nSMA {min(periods)} vs SMA {max(periods)}\n", "-"*30, sep="")

    dfs = _divide_zones(df)
    column = f'sma_{min(periods)}_vs_sma_{max(periods)}'

    favourables = _make_values_from_dfs([df[df[column] == 1] for df in dfs], column, 'count')
    unfavourables = _make_values_from_dfs([df[df[column] == -1] for df in dfs], column, 'count')

    fav_labels = _get_labels('_fav_count')
    unfav_labels = _get_labels('_unfav_count')

    values = [*favourables, *unfavourables]
    labels = [*fav_labels, *unfav_labels]

    title = f"SMA {min(periods)} vs SMA {max(periods)} - Relationship"

    _plot_feature(values, labels, title)

def plot_lower_sma_vs_higher_sma_pct(df: pd.DataFrame, periods: list[int]) -> None:

    print(f"\nSMA {min(periods)} vs SMA {max(periods)}, by percentages\n", "-"*30, sep="")

    dfs = _divide_zones(df)
    column = f'sma_{min(periods)}_vs_sma_{max(periods)}'

    favourables = _make_values_from_dfs([df[df[column] == 1] for df in dfs], column, 'count', pct=True, raw_df=df)
    unfavourables = _make_values_from_dfs([df[df[column] == -1] for df in dfs], column, 'count', pct=True, raw_df=df)

    fav_labels = _get_labels('_fav_count_pct')
    unfav_labels = _get_labels('_unfav_count_pct')

    values = [*favourables, *unfavourables]
    labels = [*fav_labels, *unfav_labels]

    title = f"SMA {min(periods)} vs SMA {max(periods)} - Relationship percentage"

    _plot_feature(values, labels, title, pct=True)


# =============================================================================
# MOMENTUM MAGNITUDE OF SMA
# =============================================================================


def plot_momentum_magnitude_gap(df: pd.DataFrame, periods: list[int]) -> None:

    print(f"\nMomentum Magnitude Gap, SMA {min(periods)} vs SMA {max(periods)}\n", "-"*30, sep="")

    dfs = _divide_zones(df)
    column = 'momentum_magnitude_gap'

    values = _make_values_from_dfs(dfs, column, 'std')
    labels = _get_labels('_std')

    title = f"Momentum Magnitude Gap, SMA {min(periods)} vs SMA {max(periods)}"

    _plot_feature(values, labels, title)


def plot_momentum_magnitude_diff(df: pd.DataFrame, periods: list[int], shift: int = 1) -> None:

    print(f"\nMomentum Magnitude Diff, SMA {min(periods)} vs SMA {max(periods)}\n", "-"*30, sep="")

    dfs = _divide_zones(df)
    column = f'momentum_magnitude_gap_shift_by_{shift}'

    values = _make_values_from_dfs(dfs, column, 'std')
    labels = _get_labels('_std')

    title = f"Momentum Magnitude Diff, SMA {min(periods)} vs SMA {max(periods)}"

    _plot_feature(values, labels, title)