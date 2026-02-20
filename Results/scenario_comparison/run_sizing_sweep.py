"""Sweep battery sizes for DA+DCM and DCM-only scenarios."""
import json
import subprocess
import shutil
import os
import csv

BASE_DIR = "/Users/fsl/Documents/GitHub/DER-VET"
INPUT_JSON = os.path.join(BASE_DIR, "Results/DER-VET_20260218180027/inputs/model_parameters.json")
RESULTS_DIR = os.path.join(BASE_DIR, "Results/DER-VET_20260218180027/results")
OUTPUT_DIR = os.path.join(BASE_DIR, "Results/scenario_comparison")

BATTERY_CONFIGS = [
    {"power_kw": 50,  "energy_kwh": 100,  "duration_hr": 2},
    {"power_kw": 100, "energy_kwh": 200,  "duration_hr": 2},
    {"power_kw": 100, "energy_kwh": 400,  "duration_hr": 4},
    {"power_kw": 150, "energy_kwh": 300,  "duration_hr": 2},
    {"power_kw": 150, "energy_kwh": 600,  "duration_hr": 4},
    {"power_kw": 200, "energy_kwh": 400,  "duration_hr": 2},
    {"power_kw": 200, "energy_kwh": 800,  "duration_hr": 4},
    {"power_kw": 250, "energy_kwh": 500,  "duration_hr": 2},
    {"power_kw": 250, "energy_kwh": 1000, "duration_hr": 4},
]

SCENARIOS = [
    {"name": "DA_DCM",       "da": True,  "dcm": True,  "retail": False, "cp": False},
    {"name": "DCM_retail",   "da": False, "dcm": True,  "retail": True,  "cp": False},
    {"name": "DA_DCM_CP",    "da": True,  "dcm": True,  "retail": False, "cp": True},
    {"name": "DCM_retail_CP","da": False, "dcm": True,  "retail": True,  "cp": True},
    {"name": "CP_only",      "da": False, "dcm": False, "retail": False, "cp": True},
]


def set_json_value(data, key_path, value):
    """Set a nested JSON value using dot-separated keys where the structure
    uses the DER-VET opt_value pattern."""
    obj = data
    for key in key_path[:-1]:
        obj = obj[key]
    obj[key_path[-1]]["opt_value"] = str(value)


def configure_battery(data, power_kw, energy_kwh):
    """Update battery size parameters in the model JSON."""
    batt_keys = data["tags"]["Battery"]
    batt_id = list(batt_keys.keys())[0]
    batt = batt_keys[batt_id]["keys"]
    batt["ch_max_rated"]["opt_value"] = str(power_kw)
    batt["dis_max_rated"]["opt_value"] = str(power_kw)
    batt["ene_max_rated"]["opt_value"] = str(energy_kwh)
    batt["ccost_kW"]["opt_value"] = "550"
    batt["ccost_kWh"]["opt_value"] = "180"


def configure_cp(data, cp_on, capacity_rate=21.186, transmission_rate=13.7091,
                  pjm_5cp_dates="2025-06-23:18,2025-06-24:18,2025-06-25:15,2025-07-28:18,2025-07-29:18",
                  utility_1cp_dates="2025-06-24:19", growth=3):
    """Toggle CP value stream and set rates/dates."""
    tags = data["tags"]
    if "CP" not in tags:
        tags["CP"] = {"": {"active": "no"}}
    cp_id = list(tags["CP"].keys())[0]
    tags["CP"][cp_id]["active"] = "yes" if cp_on else "no"
    if cp_on:
        tags["CP"][cp_id]["keys"] = {
            "capacity_rate_monthly": {
                "opt_value": str(capacity_rate),
                "sensitivity": {"active": "no", "coupled": "None", "value": "nan"},
                "type": "float"
            },
            "transmission_rate_monthly": {
                "opt_value": str(transmission_rate),
                "sensitivity": {"active": "no", "coupled": "None", "value": "nan"},
                "type": "float"
            },
            "pjm_5cp_dates": {
                "opt_value": pjm_5cp_dates,
                "sensitivity": {"active": "no", "coupled": "None", "value": "nan"},
                "type": "string"
            },
            "utility_1cp_dates": {
                "opt_value": utility_1cp_dates,
                "sensitivity": {"active": "no", "coupled": "None", "value": "nan"},
                "type": "string"
            },
            "growth": {
                "opt_value": str(growth),
                "sensitivity": {"active": "no", "coupled": "None", "value": "nan"},
                "type": "float"
            },
        }


def configure_services(data, da_on, dcm_on, retail_on, cp_on=False):
    """Toggle value streams on/off."""
    tags = data["tags"]
    da_id = list(tags["DA"].keys())[0]
    dcm_id = list(tags["DCM"].keys())[0]
    retail_id = list(tags["retailTimeShift"].keys())[0]

    tags["DA"][da_id]["active"] = "yes" if da_on else "no"
    tags["DCM"][dcm_id]["active"] = "yes" if dcm_on else "no"
    tags["retailTimeShift"][retail_id]["active"] = "yes" if retail_on else "no"

    if da_on and "keys" not in tags["DA"][da_id]:
        tags["DA"][da_id]["keys"] = {
            "growth": {
                "opt_value": "0",
                "sensitivity": {"active": "no", "coupled": "None", "value": "nan"},
                "type": "float"
            }
        }

    configure_cp(data, cp_on)


def run_dervet(json_path):
    """Run DER-VET and return exit code."""
    result = subprocess.run(
        ["conda", "run", "-n", "dervet-venv", "python", "run_DERVET.py", json_path],
        cwd=BASE_DIR,
        capture_output=True, text=True, timeout=120
    )
    return result.returncode, result.stdout, result.stderr


def extract_results(results_dir):
    """Extract key metrics from results."""
    metrics = {}

    # Pro forma year 1
    pf_path = os.path.join(results_dir, "pro_forma.csv")
    if os.path.exists(pf_path):
        with open(pf_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if len(rows) >= 2:
                yr1 = rows[1]  # second data row = first operating year
                metrics["yearly_net_value"] = float(yr1.get("Yearly Net Value", 0))
                metrics["avoided_demand_charge"] = float(yr1.get("Avoided Demand Charge", 0)) if "Avoided Demand Charge" in yr1 else 0
                metrics["da_ets"] = float(yr1.get("DA ETS", 0)) if "DA ETS" in yr1 else 0
                metrics["avoided_cp_capacity"] = float(yr1.get("Avoided CP Capacity Charges", 0)) if "Avoided CP Capacity Charges" in yr1 else 0
                metrics["avoided_cp_transmission"] = float(yr1.get("Avoided CP Transmission Charges", 0)) if "Avoided CP Transmission Charges" in yr1 else 0
                metrics["fixed_om"] = float(yr1.get("BATTERY: bess 1 Fixed O&M Cost", 0))

    # NPV
    npv_path = os.path.join(results_dir, "npv.csv")
    if os.path.exists(npv_path):
        with open(npv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics["npv"] = float(row.get("Lifetime Present Value", 0))

    # Payback
    pb_path = os.path.join(results_dir, "payback.csv")
    if os.path.exists(pb_path):
        with open(pb_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Metric"] == "Payback Period":
                    try:
                        metrics["payback_years"] = float(row["Value"])
                    except (ValueError, TypeError):
                        metrics["payback_years"] = float('inf')

    return metrics


def main():
    with open(INPUT_JSON) as f:
        base_data = json.load(f)

    all_results = []

    for scenario in SCENARIOS:
        for batt in BATTERY_CONFIGS:
            label = f"{scenario['name']}_{batt['power_kw']}kW_{batt['energy_kwh']}kWh"
            print(f"\n{'='*60}")
            print(f"Running: {label}")
            print(f"{'='*60}")

            data = json.loads(json.dumps(base_data))

            configure_battery(data, batt["power_kw"], batt["energy_kwh"])
            configure_services(data, scenario["da"], scenario["dcm"], scenario["retail"], scenario.get("cp", False))

            with open(INPUT_JSON, 'w') as f:
                json.dump(data, f, indent=2)

            rc, stdout, stderr = run_dervet(INPUT_JSON)

            if rc != 0:
                print(f"  FAILED (exit code {rc})")
                print(f"  stderr: {stderr[-500:]}")
                continue

            metrics = extract_results(RESULTS_DIR)
            metrics["scenario"] = scenario["name"]
            metrics["power_kw"] = batt["power_kw"]
            metrics["energy_kwh"] = batt["energy_kwh"]
            metrics["duration_hr"] = batt["duration_hr"]
            all_results.append(metrics)

            dest = os.path.join(OUTPUT_DIR, label)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(RESULTS_DIR, dest)

            print(f"  NPV: ${metrics.get('npv', 0):,.0f}")
            print(f"  Avoided DC: ${metrics.get('avoided_demand_charge', 0):,.0f}/yr")
            print(f"  DA ETS: ${metrics.get('da_ets', 0):,.0f}/yr")
            cp_cap = metrics.get('avoided_cp_capacity', 0)
            cp_tx = metrics.get('avoided_cp_transmission', 0)
            if cp_cap or cp_tx:
                print(f"  Avoided CP Capacity: ${cp_cap:,.0f}/yr")
                print(f"  Avoided CP Transmission: ${cp_tx:,.0f}/yr")
            print(f"  Net annual: ${metrics.get('yearly_net_value', 0):,.0f}/yr")

    # Summary table
    print(f"\n\n{'='*100}")
    print("SUMMARY TABLE")
    print(f"{'='*100}")
    header = (f"{'Scenario':<18} {'Power':>8} {'Energy':>8} {'Dur':>5} "
              f"{'Avoided DC':>12} {'DA ETS':>12} {'CP Cap':>10} {'CP Tx':>10} "
              f"{'Net Annual':>12} {'NPV':>14} {'Payback':>10}")
    print(header)
    print("-" * len(header))
    for r in all_results:
        pb = r.get('payback_years', float('inf'))
        pb_str = f"{pb:.1f}" if pb < 100 else "Never"
        print(f"{r['scenario']:<18} {r['power_kw']:>6}kW {r['energy_kwh']:>6}kWh {r['duration_hr']:>4}h "
              f"${r.get('avoided_demand_charge', 0):>10,.0f} ${r.get('da_ets', 0):>10,.0f} "
              f"${r.get('avoided_cp_capacity', 0):>8,.0f} ${r.get('avoided_cp_transmission', 0):>8,.0f} "
              f"${r.get('yearly_net_value', 0):>10,.0f} ${r.get('npv', 0):>12,.0f} {pb_str:>10}")

    # Save summary CSV
    summary_path = os.path.join(OUTPUT_DIR, "summary.csv")
    if all_results:
        with open(summary_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()
