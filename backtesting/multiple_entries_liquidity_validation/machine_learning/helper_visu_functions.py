import matplotlib.pyplot as plt
import numpy as np


# Helper function to plot the impurity-based feature importances of the defined model
def plot_impurity_based_feature_importance_single_chart(model, X):

    fig, ax = plt.subplots(figsize=(14,6))

    tree_feature_importance_sorted = np.argsort(model.feature_importances_)
    tree_indices = np.arange(0, len(model.feature_importances_)) +0.5

    ax.barh(tree_indices, model.feature_importances_[tree_feature_importance_sorted],
            height=0.7, color='#B2D7D0')
    ax.set_yticks(tree_indices)
    ax.set_yticklabels(X.columns[tree_feature_importance_sorted], fontsize=12)
    ax.set_ylim((0, len(model.feature_importances_)))
    ax.set_xlabel("Impurity Based Feature Importance", fontsize=16)
    ax.set_title("Single Tree, model: Random Forest", fontsize=18)

    fig.tight_layout()
    plt.show()

def plot_impurity_based_feature_importance_comparison(m1, m2, X1, X2):
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14,6))

    tree_feature_importance_sorted_m1 = np.argsort(m1.feature_importances_)
    tree_indices_m1 = np.arange(0, len(m1.feature_importances_)) +0.5

    ax1.barh(tree_indices_m1, m1.feature_importances_[tree_feature_importance_sorted_m1],
             height=0.7, color='#B2D7D0')
    ax1.set_yticks(tree_indices_m1)
    ax1.set_yticklabels(X1.columns[tree_feature_importance_sorted_m1], fontsize=12)
    ax1.set_ylim((0, len(m1.feature_importances_)))
    ax1.set_xlabel("Imputiry Based Feature Importance", fontsize=16)
    ax1.set_title("Winners")

    tree_feature_importance_sorted_m2 = np.argsort(m2.feature_importances_)
    tree_indices_m2 = np.arange(0, len(m2.feature_importances_)) +0.5

    ax2.barh(tree_indices_m2, m2.feature_importances_[tree_feature_importance_sorted_m2],
             height=0.7, color='#B2D7D0')
    ax2.set_yticks(tree_indices_m2)
    ax2.set_yticklabels(X2.columns[tree_feature_importance_sorted_m2], fontsize=12)
    ax2.set_ylim((0, len(m2.feature_importances_)))
    ax2.set_xlabel("Imputiry Based Feature Importance", fontsize=16)
    ax2.set_title("Losers")

    fig.tight_layout()
    plt.show()


def plot_sma_distance_from_zone(df, period: int) -> None:

    winners_before = df[(df['year'] <= 2023) & (df['profitable'] > 0)][f'sma_{period}_distance_from_zone'].std()
    winners_after = df[(df['year'] >= 2024) & (df['profitable'] > 0)][f'sma_{period}_distance_from_zone'].std()
    losers_before = df[(df['year'] <= 2023) & (df['profitable'] <= 0)][f'sma_{period}_distance_from_zone'].std()
    losers_after = df[(df['year'] >= 2024) & (df['profitable'] <= 0)][f'sma_{period}_distance_from_zone'].std()

    values = [winners_before, winners_after, losers_before, losers_after]
    labels = ['winners_before_std', 'winners_after_std', 'losers_before_std', 'losers_after_std']

    print(f"Distance values, SMA period: {period}")
    for val, lab in zip(values, labels):
        print(f"{lab} = {round(val,2)}")

    fig, ax = plt.subplots(figsize=(8,6))

    length = np.arange(0, len(values)) + 0.5

    ax.bar(length, values, color='#B2D7D0')
    ax.set_xticks(length)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_xlim(0, len(values))
    ax.set_title(f"SMA {period} - Distance from zone")
    fig.tight_layout()
    plt.show()

def plot_sma_direction(df, period: int) -> None:

    # i need to make average on those variables.. cause i am summarizing it, and before has much more zones then after.. so make it weighted mean..
    # then move on lower_sma_vs_higher_sma()

    winners_before_favorable_dir = (df[(df['year'] <= 2023) & (df['profitable'] > 0)][f'sma_{period}_direction'] == 1).sum()
    winners_after_favorable_dir = (df[(df['year'] >= 2024) & (df['profitable'] > 0)][f'sma_{period}_direction'] == 1).sum()
    losers_before_favorable_dir = (df[(df['year'] <= 2023) & (df['profitable'] <= 0)][f'sma_{period}_direction'] == 1).sum()
    losers_after_favorable_dir = (df[(df['year'] >= 2024) & (df['profitable'] <= 0)][f'sma_{period}_direction'] == 1).sum()

    winners_before_unfavorable_dir = (df[(df['year'] <= 2023) & (df['profitable'] > 0)][f'sma_{period}_direction'] == -1).sum()
    winners_after_unfavorable_dir = (df[(df['year'] >= 2024) & (df['profitable'] > 0)][f'sma_{period}_direction'] == -1).sum()
    losers_before_unfavorable_dir = (df[(df['year'] <= 2023) & (df['profitable'] <= 0)][f'sma_{period}_direction'] == -1).sum()
    losers_after_unfavorable_dir = (df[(df['year'] >= 2024) & (df['profitable'] <= 0)][f'sma_{period}_direction'] == -1).sum()

    values = [
        winners_before_favorable_dir, winners_after_favorable_dir, losers_before_favorable_dir, losers_after_favorable_dir,
        winners_before_unfavorable_dir, winners_after_unfavorable_dir, losers_before_unfavorable_dir, losers_after_unfavorable_dir
    ]
    labels = [
        'winners_before_favorable_dir', 'winners_after_favorable_dir', 'losers_before_favorable_dir', 'losers_after_favorable_dir',
        'winners_before_unfavorable_dir', 'winners_after_unfavorable_dir', 'losers_before_unfavorable_dir', 'losers_after_unfavorable_dir'
    ]

    print(f"Direction values, SMA period: {period}")
    for val, lab in zip(values, labels):
        print(f"{lab} = {round(val,2)}")

    fig, ax = plt.subplots(figsize=(14,10))

    length = np.arange(0, len(values)) + 0.5

    ax.bar(length, values, color='#B2D7D0')
    ax.set_xticks(length)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_xlim(0, len(values))
    ax.set_title(f"SMA {period} - Direction")
    fig.tight_layout()
    plt.show()