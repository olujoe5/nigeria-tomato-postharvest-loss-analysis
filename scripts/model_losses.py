"""
Nigeria Tomato Post-Harvest Loss Model
========================================
Kano-Lagos corridor case study.

Reads the raw, cited source tables in /data and produces a single modeled
output table suitable for loading into SQL and visualizing in Power BI.

All figures are either:
  (a) ACTUAL published statistics (tagged 'actual' in source data), or
  (b) ANALYST ESTIMATES derived transparently from published ranges/rankings
      (tagged 'estimated' in source data)

See data/sources.csv for full citations and README.md for the
full explanation of every assumption.

Author: Joseph Olumide
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "data"

# Cold-chain / logistics intervention effect size (Source S8: Ohagwu et al. 2021,
# charcoal cooler storage bins reduced postharvest losses by up to 30%)
COLD_CHAIN_LOSS_REDUCTION_PCT = 30

# Which downstream stages the cold-chain fix realistically affects.
# A charcoal cooler / basic cold-chain intervention mainly helps once produce
# is harvested and needs to survive transport + time-to-sale - so we apply it
# to postharvest handling, transport, wholesale, and retail, but NOT to
# farm/harvest-stage losses (as those are driven by pests, harvest timing, and
# handling technique, not cold storage).
COLD_CHAIN_ELIGIBLE_STAGES = {
    "Postharvest handling (on-farm sorting, packing, initial storage)",
    "Transport",
    "Wholesale market",
    "Retail",
}


def load_data():
    production = pd.read_csv(DATA_DIR / "state_production_estimates.csv")
    stages = pd.read_csv(DATA_DIR / "stage_loss_benchmarks.csv")
    prices = pd.read_csv(DATA_DIR / "state_prices_naira_per_kg.csv")
    return production, stages, prices


def build_model():
    production, stages, prices = load_data()

    producer_prices = prices[prices["role"] == "origin_producer"][
        ["state", "price_naira_per_kg"]
    ].rename(columns={"price_naira_per_kg": "farmgate_price_naira_per_kg"})

    # Representative downstream (market) price used to value losses that occur
    # AFTER produce leaves the farm (transport/wholesale/retail) - this matters
    # because a tonne lost at retail is worth far more than a tonne lost at the
    # farm gate, since value has already been added moving down the chain.
    national_avg_price = prices.loc[
        prices["state"] == "National_average", "price_naira_per_kg"
    ].values[0]

    rows = []
    for _, prod_row in production.iterrows():
        state = prod_row["state"]
        annual_tonnes = prod_row["est_annual_production_tonnes"]

        farmgate_price = producer_prices.loc[
            producer_prices["state"] == state, "farmgate_price_naira_per_kg"
        ]
        farmgate_price = (
            farmgate_price.values[0] if len(farmgate_price) else national_avg_price
        )

        for _, stage_row in stages.iterrows():
            stage_name = stage_row["stage"]
            loss_pct_of_original = stage_row["derived_loss_pct_of_volume_entering_chain"]

            tonnes_lost_baseline = annual_tonnes * (loss_pct_of_original / 100)

            # Price used to value this stage's loss: farmgate price for the
            # farm/harvest stage, blended toward national average price for
            # every downstream stage (value-added-in-transit assumption)
            if stage_name == "Farm / Harvest":
                value_price = farmgate_price
            else:
                value_price = national_avg_price

            naira_lost_baseline = tonnes_lost_baseline * value_price * 1000  # tonnes -> kg

            # Cold-chain scenario: reduce loss at eligible stages only
            if stage_name in COLD_CHAIN_ELIGIBLE_STAGES:
                tonnes_lost_coldchain = tonnes_lost_baseline * (
                    1 - COLD_CHAIN_LOSS_REDUCTION_PCT / 100
                )
            else:
                tonnes_lost_coldchain = tonnes_lost_baseline

            naira_lost_coldchain = tonnes_lost_coldchain * value_price * 1000
            naira_saved = naira_lost_baseline - naira_lost_coldchain
            tonnes_saved = tonnes_lost_baseline - tonnes_lost_coldchain

            rows.append(
                {
                    "state": state,
                    "region": prod_row["region"],
                    "annual_production_tonnes": annual_tonnes,
                    "stage": stage_name,
                    "stage_order": stage_row["stage_order"],
                    "loss_pct_of_original_volume": loss_pct_of_original,
                    "tonnes_lost_baseline": round(tonnes_lost_baseline, 1),
                    "naira_lost_baseline": round(naira_lost_baseline, 0),
                    "cold_chain_applied": stage_name in COLD_CHAIN_ELIGIBLE_STAGES,
                    "tonnes_lost_with_coldchain": round(tonnes_lost_coldchain, 1),
                    "naira_lost_with_coldchain": round(naira_lost_coldchain, 0),
                    "tonnes_saved_by_coldchain": round(tonnes_saved, 1),
                    "naira_saved_by_coldchain": round(naira_saved, 0),
                    "value_price_naira_per_kg_used": value_price,
                }
            )

    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame):
    print("\n=== NATIONAL SUMMARY (Kano-Lagos corridor producer states) ===")
    total_production = df.drop_duplicates("state")["annual_production_tonnes"].sum()
    total_lost_baseline = df["tonnes_lost_baseline"].sum()
    total_naira_baseline = df["naira_lost_baseline"].sum()
    total_naira_coldchain = df["naira_lost_with_coldchain"].sum()
    total_naira_saved = df["naira_saved_by_coldchain"].sum()

    print(f"Total annual production modeled: {total_production:,.0f} tonnes")
    print(
        f"Total tonnes lost (baseline):     {total_lost_baseline:,.0f} tonnes "
        f"({total_lost_baseline/total_production*100:.1f}% of production)"
    )
    print(f"Total value lost (baseline):      N{total_naira_baseline:,.0f}")
    print(f"Total value lost (with cold-chain fix): N{total_naira_coldchain:,.0f}")
    print(f"TOTAL ANNUAL SAVINGS FROM COLD-CHAIN FIX: N{total_naira_saved:,.0f}")

    print("\n=== LOSS BY STAGE (national, baseline) ===")
    by_stage = (
        df.groupby(["stage_order", "stage"])[["naira_lost_baseline", "tonnes_lost_baseline"]]
        .sum()
        .sort_index()
    )
    print(by_stage.to_string())

    print("\n=== LOSS BY STATE (baseline, naira) ===")
    by_state = (
        df.groupby("state")["naira_lost_baseline"]
        .sum()
        .sort_values(ascending=False)
    )
    print(by_state.to_string())


if __name__ == "__main__":
    model_df = build_model()
    output_path = OUTPUT_DIR / "tomato_loss_model_output.csv"
    model_df.to_csv(output_path, index=False)
    print(f"Model output written to: {output_path}")
    summarize(model_df)
