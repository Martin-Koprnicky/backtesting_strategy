CREATE TABLE IF NOT EXISTS "runs" (
    "id" INTEGER,
    "config_id" INTEGER,
    PRIMARY KEY("id"),
    FOREIGN KEY("config_id") REFERENCES "configs"("id")
);

CREATE TABLE IF NOT EXISTS "zones" (
    "id" INTEGER,
    "run_id" INTEGER,
    "year" INTEGER,
    "zone_type" TEXT,
    "pattern_type" TEXT,
    "exit_reason" TEXT,
    "profit_loss_net" REAL,
    "total_fees" REAL,
    PRIMARY KEY("id"),
    FOREIGN KEY("run_id") REFERENCES "runs"("id")
);

CREATE TABLE IF NOT EXISTS "configs" (
    "id" INTEGER,
    
    -- GENERAL
    "patterns" TEXT,

    -- STRATEGY
    "tp_strategy" TEXT,
    "fixed_tp" REAL,
    "one_r_strategy" TEXT,

    -- BASE
    "max_range" REAL,

    -- MOVEMENT BEFORE
    "progressive_movement_before" INTEGER CHECK("progressive_movement_before" IN (0,1)),
    "body_min_percentage_before" REAL,
    "min_strongest_candle_strength_score_before" REAL,
    "min_weakest_candle_strength_score_before" REAL,

    -- MOVEMENT AFTER
    "progressive_movement_after" INTEGER CHECK("progressive_movement_after" IN (0,1)),
    "body_min_percentage_after" REAL,
    "min_strongest_candle_strength_score_after" REAL,
    "min_weakest_candle_strength_score_after" REAL,

    -- LIQUIDITY VALIDATION
    "retracement_percentage_min" REAL,
    "retracement_percentage_max" REAL,
    "wick_allowed_during_validation" INTEGER CHECK("wick_allowed_during_validation" IN (0,1)),

    -- TRADING PARAMETERS
    "entry_levels" TEXT,
    "stop_loss_moved" REAL,

    -- RISK
    "zone_risk" REAL,
    "entry_risk" REAL,

    -- FEES
    "entry_threshold" REAL,

    -- KEYS
    PRIMARY KEY("id")
);

