import matplotlib.pyplot as plt
import pandas as pd
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

