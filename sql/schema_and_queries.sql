-- =========================================================
-- Nigeria Tomato Post-Harvest Loss Model - SQL layer
-- Load tomato_loss_model_output.csv into this table, then run
-- the queries below.
-- Tested against SQLite.
-- =========================================================

DROP TABLE IF EXISTS tomato_loss_model;

CREATE TABLE tomato_loss_model (
    state                           TEXT,
    region                          TEXT,
    annual_production_tonnes        REAL,
    stage                           TEXT,
    stage_order                     INTEGER,
    loss_pct_of_original_volume     REAL,
    tonnes_lost_baseline            REAL,
    naira_lost_baseline             REAL,
    cold_chain_applied              TEXT,
    tonnes_lost_with_coldchain      REAL,
    naira_lost_with_coldchain       REAL,
    tonnes_saved_by_coldchain       REAL,
    naira_saved_by_coldchain        REAL,
    value_price_naira_per_kg_used   REAL
);

-- Example load command (SQLite CLI):
-- .mode csv
-- .import --skip 1 data/tomato_loss_model_output.csv tomato_loss_model


-- =========================================================
-- QUERY 1: National headline numbers 
-- =========================================================
SELECT
    (SELECT SUM(annual_production_tonnes) FROM
        (SELECT DISTINCT state, annual_production_tonnes FROM tomato_loss_model) AS distinct_states) AS total_production_tonnes,
    SUM(tonnes_lost_baseline)                                  AS total_tonnes_lost_baseline,
    SUM(naira_lost_baseline)                                   AS total_naira_lost_baseline,
    SUM(naira_lost_with_coldchain)                              AS total_naira_lost_coldchain,
    SUM(naira_saved_by_coldchain)                               AS total_naira_saved_by_coldchain,
    ROUND(100.0 * SUM(tonnes_lost_baseline) /
        (SELECT SUM(annual_production_tonnes) FROM
            (SELECT DISTINCT state, annual_production_tonnes FROM tomato_loss_model) AS distinct_states2), 1) AS overall_loss_pct
FROM tomato_loss_model;


-- =========================================================
-- QUERY 2: Loss by stage
-- =========================================================
SELECT
    stage_order,
    stage,
    SUM(tonnes_lost_baseline)        AS tonnes_lost,
    SUM(naira_lost_baseline)         AS naira_lost,
    ROUND(100.0 * SUM(naira_lost_baseline) /
        (SELECT SUM(naira_lost_baseline) FROM tomato_loss_model), 1) AS pct_of_total_naira_lost
FROM tomato_loss_model
GROUP BY stage_order, stage
ORDER BY stage_order;


-- =========================================================
-- QUERY 3: Loss by state 
-- =========================================================
SELECT
    state,
    region,
    MAX(annual_production_tonnes)   AS annual_production_tonnes,
    SUM(tonnes_lost_baseline)       AS tonnes_lost,
    SUM(naira_lost_baseline)        AS naira_lost,
    SUM(naira_saved_by_coldchain)   AS naira_recoverable_with_coldchain
FROM tomato_loss_model
GROUP BY state, region
ORDER BY naira_lost DESC;


-- =========================================================
-- QUERY 4: Before vs after cold-chain comparison, by stage
-- =========================================================
SELECT
    MIN(stage_order)                 AS stage_order,
    stage,
    cold_chain_applied,
    SUM(naira_lost_baseline)         AS naira_lost_before,
    SUM(naira_lost_with_coldchain)   AS naira_lost_after,
    SUM(naira_saved_by_coldchain)    AS naira_saved
FROM tomato_loss_model
GROUP BY stage, cold_chain_applied
ORDER BY stage_order;


-- =========================================================
-- QUERY 5: Region-level roll-up
-- =========================================================
SELECT
    region,
    SUM(tonnes_lost_baseline)      AS tonnes_lost,
    SUM(naira_lost_baseline)       AS naira_lost,
    SUM(naira_saved_by_coldchain)  AS naira_recoverable
FROM tomato_loss_model
GROUP BY region
ORDER BY naira_lost DESC;
