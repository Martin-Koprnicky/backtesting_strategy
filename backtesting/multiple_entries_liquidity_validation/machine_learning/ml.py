import pandas as pd
import numpy as np

from data.data_handlers import get_data
from backtesting.multiple_entries_liquidity_validation.machine_learning.models_plots import (
    plot_impurity_based_feature_importance_single_chart,
    plot_impurity_based_feature_importance_comparison,
    
)
from backtesting.multiple_entries_liquidity_validation.machine_learning.features_plots import (
    plot_sma_distance_from_zone,
    plot_sma_direction,
    plot_sma_direction_pct,
    plot_lower_sma_vs_higher_sma,
)

from backtesting.multiple_entries_liquidity_validation.machine_learning.indicators import IndicatorCalculator

from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from sklearn.ensemble import RandomForestClassifier

from datetime import datetime

random_state = 44

def run_ml():

    for i in [1, 5, 10, 20]:

        df = pd.read_csv('backtesting/multiple_entries_liquidity_validation/measure_zones.csv')

        zones, winners, losers = _modify_dataframe(df)

        full_data = []

        for year in [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]:
            data = get_data(type='parquet', year=year, timeframes=['1h'])
            full_data.append(data['1h'])

        indi_vals_df = pd.concat(full_data)

        calculator = IndicatorCalculator(zones)

        periods = [20,9]

        for period in periods:
            calculator.sma(df=indi_vals_df, period=period, shift=i)

        merged_zones = calculator.merge_zones_with_indi_vals(indi_vals_df, zones)

        calculator.distance_SMA_from_zone(merged_zones, periods)
        calculator.direction_of_SMA_at_lq_validation(merged_zones, periods)
        calculator.lower_sma_vs_higher_sma(merged_zones, periods)
        
        for period in periods:
            plot_sma_distance_from_zone(merged_zones, period)
            plot_sma_direction(merged_zones, period)
            plot_sma_direction_pct(merged_zones, period)
        
        #plot_lower_sma_vs_higher_sma(merged_zones)

    return
    rfc_full_df, X_full_df, y_full_df = _random_forest_classifier(df)
    rfc_winners, X_winners, y_winners = _random_forest_classifier(winners)
    rfc_losers, X_losers, y_losers = _random_forest_classifier(losers)
    
    
    # Helper code to visualize the feature importance using 'MDI'
    #plot_impurity_based_feature_importance_single_chart(rfc_full_df, X_full_df)
    #plot_impurity_based_feature_importance_comparison(rfc_winners, rfc_losers, X_winners, X_losers)


def _get_fraction_of_data(data: pd.DataFrame, measuring_time: datetime, period: int) -> pd.DataFrame:
    ...
    

def _random_forest_classifier(df: pd.DataFrame) -> RandomForestClassifier:

    train_data = df[df['year'] <= 2023]
    test_data = df[df['year'] >= 2024]

    train_data = train_data.drop('year', axis=1)
    test_data = test_data.drop('year', axis=1)

    X = df.drop('profitable', axis=1)
    y = df['profitable']

    X_train = train_data.drop('profitable', axis=1)
    y_train = train_data['profitable']
    
    X_test = test_data.drop('profitable', axis=1)
    y_test = test_data['profitable']

    random_forest = RandomForestClassifier(random_state=random_state).fit(X_train, y_train)

    predictions = random_forest.predict(X_test)
    acc_rf = round(accuracy_score(predictions, y_test), 2)

    print(f'For Random Forest, the accuracy on the validation set is {acc_rf}')

    return random_forest, X, y

    
def _modify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Modifying Dataframe for ML usage from raw CSV file."""
    df['profitable'] = [1 if profit > 0 else 0 for profit in df['pnl']]
    df['zone_type'] = [1 if zone_type == 'demand' else 0 for zone_type in df['zone_type']]
    df['is_RBR'] = [1 if pattern == 'rally_base_rally' else 0 for pattern in df['pattern_type']]
    df['is_RBD'] = [1 if pattern == 'rally_base_drop' else 0 for pattern in df['pattern_type']]
    df['is_DBR'] = [1 if pattern == 'drop_base_rally' else 0 for pattern in df['pattern_type']]
    df['is_DBD'] = [1 if pattern == 'drop_base_drop' else 0 for pattern in df['pattern_type']]

    df = df.drop('pnl', axis=1)
    df = df.drop('pattern_type', axis=1)

    winners = df[df['profitable'] == 1]
    losers = df[df['profitable'] == 0]

    return df, winners, losers

def main():
    run_ml()




if __name__ == "__main__":
    main()