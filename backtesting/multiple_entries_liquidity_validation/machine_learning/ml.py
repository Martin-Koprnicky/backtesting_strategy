import pandas as pd
import numpy as np

from data.data_handlers import get_data
from backtesting.multiple_entries_liquidity_validation.machine_learning.helper_visu_functions import (
    plot_impurity_based_feature_importance_single_chart,
    plot_impurity_based_feature_importance_comparison,
    plot_winners_losers_before_and_after
)

from backtesting.multiple_entries_liquidity_validation.machine_learning.indicators import IndicatorCalculator

from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from sklearn.ensemble import RandomForestClassifier

from datetime import datetime

random_state = 44

def run_ml():

    df = pd.read_csv('backtesting/multiple_entries_liquidity_validation/measure_zones.csv')

    df, winners, losers = _modify_dataframe(df)

    full_data = []

    for year in [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]:
        data = get_data(type='parquet', year=year, timeframes=['1h'])
        full_data.append(data['1h'])

    pd_full_data = pd.concat(full_data)

    calculator = IndicatorCalculator()

    data_with_sma = calculator.sma(df=pd_full_data, period=20)

    data_with_distances = calculator.distance_SMA_from_zone(data_with_sma, df)

    plot_winners_losers_before_and_after(data_with_distances)

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