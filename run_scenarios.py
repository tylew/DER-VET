#!/usr/bin/env python
"""Run multiple DER-VET scenarios and generate comparison plots.

Edit the SCENARIOS list below to define what gets run.  Each scenario
specifies battery size, active value-stream services, and CP events.
Results are saved under Results/scenario_comparison/<scenario_name>/
with a plots/ subfolder.

Usage (from repo root, with dervet-venv activated):
    python run_scenarios.py              # run all scenarios
    python run_scenarios.py --plots-only # skip DER-VET, regenerate plots only
"""
import argparse
import csv
import os
import sys

from scenario_tools.runner import run_scenario
from scenario_tools.plots import generate_all_plots

# ──────────────────────────────────────────────────────────────────────────────
# PATHS  (relative to this file, which lives at repo root)
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_JSON = os.path.join(BASE_DIR, "Results/facility_70/inputs/model_parameters.json")
INPUT_DIR = os.path.join(BASE_DIR, "Results/facility_70/inputs")
RAW_RESULTS_DIR = os.path.join(BASE_DIR, "Results/facility_70/results")
OUTPUT_ROOT = os.path.join(BASE_DIR, "Results/scenario_comparison")

# ──────────────────────────────────────────────────────────────────────────────
# SCENARIO DEFINITIONS  --  edit this section to change what gets simulated
# ──────────────────────────────────────────────────────────────────────────────

PJM_5CP_2025 = {
    "id": "pjm_5cp_2025",
    "label": "PJM 5CP 2025",
    "rate_monthly": 21.186,     # $/kW-mo
    "dates": "2025-06-23:18,2025-06-24:18,2025-06-25:15,2025-07-28:18,2025-07-29:18",
    "growth": 3,
}

PJM_5CP_2024 = {
    "id": "pjm_5cp_2024",
    "label": "PJM 5CP 2024",
    "rate_monthly": 21.186,     # $/kW-mo
    "dates": "2024-06-21:18,2024-07-16:18,2024-08-01:18,2024-08-28:18,2024-07-15:18",
    "growth": 3,
}

PSEG_5CP_2024 = {
    "id": "pseg_5cp_2024",
    "label": "PSEG 5CP 2024",
    "rate_monthly": 13.7091,       # $/kW-mo  
    "dates": "2024-07-09:18,2024-07-10:18,2024-07-15:19,2024-07-16:18,2024-08-01:19",
    "growth": 3,
}

PSEG_5CP_2025_FAKED = {
    "id": "pseg_5cp_2025_fake",
    "label": "PSEG 5CP 2025 Fake",
    "rate_monthly": 13.7091,       # $/kW-mo  
    "dates": "2025-07-09:18,2025-07-10:18,2025-07-15:19,2025-07-16:18,2025-08-01:19",
    "growth": 3,
}

JCPL_1CP_2025 = {
    "id": "jcpl_1cp_2025",
    "label": "JCPL 1CP",
    "rate_monthly": 13.7091,    # $/kW-mo
    "dates": "2025-06-24:18",
    "growth": 3,
}

SCENARIOS = [
    {
        "name": "DA_DCM_CP",
        "battery": {"power_kw": 250, "energy_kwh": 500},
        "services": {"da": True, "dcm": True, "retail": False},
        "cp_events": [PJM_5CP_2025, PSEG_5CP_2025_FAKED],
    },
    {
        "name": "CP_only",
        "battery": {"power_kw": 250, "energy_kwh": 500},
        "services": {"da": False, "dcm": False, "retail": False},
        "cp_events": [PJM_5CP_2025, PSEG_5CP_2025_FAKED],
    },
    {
        "name": "DCM_retail_CP",
        "battery": {"power_kw": 250, "energy_kwh": 500},
        "services": {"da": False, "dcm": True, "retail": True},
        "cp_events": [PJM_5CP_2025, PSEG_5CP_2025_FAKED],
    },
    {
        "name": "DA_DCM_noCP",
        "battery": {"power_kw": 250, "energy_kwh": 500},
        "services": {"da": True, "dcm": True, "retail": False},
        "cp_events": [],
    },
    {
        "name": "DCM_retail_noCP",
        "battery": {"power_kw": 250, "energy_kwh": 500},
        "services": {"da": False, "dcm": True, "retail": True},
        "cp_events": [],
    },
    # {
    #     "name": "original_DCM_retail_CP",
    #     "battery": {"power_kw": 250, "energy_kwh": 500},
    #     "services": {"da": False, "dcm": True, "retail": True},
    #     "cp_events": [PJM_5CP_2025, JCPL_1CP_2025],
    # },
    # {
    #     "name": "original_DA_DCM_CP",
    #     "battery": {"power_kw": 250, "energy_kwh": 500},
    #     "services": {"da": True, "dcm": True, "retail": False},
    #     "cp_events": [PJM_5CP_2025, JCPL_1CP_2025],
    # },
]

# ──────────────────────────────────────────────────────────────────────────────
# END SCENARIO DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────


def _print_summary(all_results, cp_ids):
    print(f"\n\n{'='*120}")
    print("SUMMARY TABLE")
    print(f"{'='*120}")

    cp_headers = "  ".join(f"{'CP:'+cid:>14}" for cid in cp_ids)
    header = (f"{'Scenario':<24}  {'Power':>6}  {'Energy':>7}"
              f"  {'Avoided DC':>12}  {'DA ETS':>12}"
              f"  {cp_headers}"
              f"  {'Gross Savings':>14}  {'NPV':>14}  {'Payback':>8}")
    print(header)
    print("-" * len(header))

    for r in all_results:
        pb = r.get("payback_years", float("inf"))
        pb_str = f"{pb:.1f}yr" if pb < 100 else "Never"
        cp_vals = "  ".join(
            f"${r.get(f'avoided_cp_{cid}', 0):>13,.0f}" for cid in cp_ids
        )
        print(f"{r['scenario']:<24}  {str(r['power_kw'])+'kW':>6}  {str(r['energy_kwh'])+'kWh':>7}"
              f"  ${r.get('avoided_demand_charge', 0):>11,.0f}  ${r.get('da_ets', 0):>11,.0f}"
              f"  {cp_vals}"
              f"  ${r.get('gross_bill_savings', 0):>13,.0f}  ${r.get('npv', 0):>13,.0f}  {pb_str:>8}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plots-only", action="store_true",
                        help="Skip DER-VET runs; regenerate plots from existing results")
    args = parser.parse_args()

    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    all_cp_ids = sorted(set(
        ev["id"] for s in SCENARIOS for ev in s.get("cp_events", [])
    ))

    all_results = []

    for scenario in SCENARIOS:
        name = scenario["name"]
        dest = os.path.join(OUTPUT_ROOT, name)

        if not args.plots_only:
            metrics, dest = run_scenario(
                scenario, BASE_DIR, INPUT_JSON, RAW_RESULTS_DIR, OUTPUT_ROOT
            )
            if metrics is None:
                continue
            all_results.append(metrics)
        else:
            if not os.path.isdir(dest):
                print(f"  Skipping {name}: no results directory at {dest}")
                continue

        generate_all_plots(scenario, dest, INPUT_DIR)

    if all_results:
        _print_summary(all_results, all_cp_ids)

        all_keys = list(dict.fromkeys(
            k for r in all_results for k in r.keys()
        ))
        summary_path = os.path.join(OUTPUT_ROOT, "scenario_summary.csv")
        with open(summary_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, restval=0)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nSummary CSV: {summary_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
