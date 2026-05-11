import sqlite3

from pathlib import Path
from .create_db import read_schema_sql
from multiple_entries_liquidity_validation.config import Config


def run_handler(config: Config, zones: list):

    connection = read_schema_sql(open_=True)

    cursor = connection.cursor()

    config_id = _insert_config(cursor, config)
    run_id = _insert_run(cursor, config_id)
    _insert_zones(cursor, zones, run_id)
    
    connection.commit()
    connection.close()


def _insert_config(cursor, config) -> int:
    """Insert configuration into SQL database used in current backtesting."""
    cursor.execute("""
        INSERT INTO configs (
            patterns,

            tp_strategy,
            fixed_tp,
            one_r_strategy,

            max_range,

            progressive_movement_before,
            body_min_percentage_before,
            min_strongest_candle_strength_score_before,
            min_weakest_candle_strength_score_before,

            progressive_movement_after,
            body_min_percentage_after,
            min_strongest_candle_strength_score_after,
            min_weakest_candle_strength_score_after,

            retracement_percentage_min,
            retracement_percentage_max,
            wick_allowed_during_validation,

            entry_levels,
            stop_loss_moved,

            zone_risk,
            entry_risk,

            entry_threshold
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
        f"{config.general.patterns}",

        "fixed_tp" if config.strategy.fixed_tp else "mountain_tp",
        config.strategy.price_level_tp if config.strategy.fixed_tp else None,
        "full_zone" if config.strategy.full_zone_one_r else "last_entry",

        config.base.max_range,

        1 if config.movement_before.progressive_movement else 0,
        config.movement_before.body_min_percentage,
        config.movement_before.min_strongest_candle_strength_score,
        config.movement_before.min_weakest_candle_strength_score,

        1 if config.movement_after.progressive_movement else 0,
        config.movement_after.body_min_percentage,
        config.movement_after.min_strongest_candle_strength_score_after,
        config.movement_after.min_weakest_candle_strength_score_after,

        config.liquidity.retracement_percentage_min,
        config.liquidity.retracement_percentage_max,
        1 if config.liquidity.wick_allowed_during_validation else 0,

        f"{config.trading.entry_levels}",
        config.trading.stop_loss_moved,

        config.risk.zone_risk,
        config.risk.entry_risk,

        config.fees.entry_threshold
    ))

    return cursor.lastrowid

def _insert_run(cursor, config_id) -> int:
    """Insert backtested run in runs."""
    cursor.execute("INSERT INTO runs (config_id) VALUES (?)", (config_id,))

    return cursor.lastrowid

def _insert_zones(cursor, zones, run_id) -> None:
    """Insert zones traded in current backtest."""
    for zone in zones:
        cursor.execute("""
            INSERT INTO zones (
                run_id,
                year,
                zone_type,
                pattern_type,
                exit_reason,
                profit_loss_net,
                total_fees
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            zone.year,
            zone.type,
            zone.pattern,
            zone.position.exit_reason,
            zone.stats.netto,
            zone.stats.total_fees
        ))