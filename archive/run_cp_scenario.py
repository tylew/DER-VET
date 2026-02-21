"""Run a single DER-VET scenario with configurable multi-CP events.

All scenario parameters are defined at the top of this file.
Supports N discrete CP event types, each with its own rate, dates, and label.
"""
import json
import subprocess
import shutil
import os
import csv

BASE_DIR = "/Users/fsl/Documents/GitHub/DER-VET"
INPUT_JSON = os.path.join(BASE_DIR, "Results/facility_70/inputs/model_parameters.json")
RESULTS_DIR = os.path.join(BASE_DIR, "Results/facility_70/results")
OUTPUT_DIR = os.path.join(BASE_DIR, "Results/scenario_comparison")
INPUT_DIR = os.path.join(BASE_DIR, "Results/facility_70/inputs")

# ──────────────────────────────────────────────────────────────────────────────
# SCENARIO CONFIGURATION -- edit these values to change what gets run
# ──────────────────────────────────────────────────────────────────────────────

SCENARIO_NAME = "dual_5cp_plus_1cp"

BATTERY = {"power_kw": 250, "energy_kwh": 500}

SERVICES = {"da": True, "dcm": True, "retail": False}

CP_EVENTS = [
    {
        "id": "pjm_5cp",
        "label": "PJM 5CP",
        "rate_monthly": 21.186,     # $/kW-mo
        "dates": "2025-06-23:18,2025-06-24:18,2025-06-25:15,2025-07-28:18,2025-07-29:18",
        "growth": 3,
    },
    {
        "id": "pseg_5cp",
        "label": "PSEG 5CP",
        "rate_monthly": 15.0,       # $/kW-mo -- update with actual rate
        "dates": "2024-07-09:18,2024-07-10:18,2024-07-15:19,2024-07-16:18,2024-08-01:19",
        "growth": 3,
    },
    # {
    #     "id": "jcpl_1cp",
    #     "label": "JCPL 1CP",
    #     "rate_monthly": 13.7091,    # $/kW-mo
    #     "dates": "2025-06-24:19",
    #     "growth": 3,
    # },
]

# ──────────────────────────────────────────────────────────────────────────────
# END CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────


def _sensitivity_stub():
    return {"active": "no", "coupled": "None", "value": "nan"}


def configure_battery(data, power_kw, energy_kwh):
    batt_keys = data["tags"]["Battery"]
    batt_id = list(batt_keys.keys())[0]
    batt = batt_keys[batt_id]["keys"]
    batt["ch_max_rated"]["opt_value"] = str(power_kw)
    batt["dis_max_rated"]["opt_value"] = str(power_kw)
    batt["ene_max_rated"]["opt_value"] = str(energy_kwh)


def configure_services(data, da_on, dcm_on, retail_on):
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
                "sensitivity": _sensitivity_stub(),
                "type": "float"
            }
        }


def configure_cp_events(data, cp_events):
    """Write multiple CP instances into the model JSON."""
    tags = data["tags"]
    cp_block = {}
    for ev in cp_events:
        cp_block[ev["id"]] = {
            "active": "yes",
            "keys": {
                "rate_monthly": {
                    "opt_value": str(ev["rate_monthly"]),
                    "sensitivity": _sensitivity_stub(),
                    "type": "float"
                },
                "cp_dates": {
                    "opt_value": ev["dates"],
                    "sensitivity": _sensitivity_stub(),
                    "type": "string"
                },
                "label": {
                    "opt_value": ev["label"],
                    "sensitivity": _sensitivity_stub(),
                    "type": "string"
                },
                "growth": {
                    "opt_value": str(ev["growth"]),
                    "sensitivity": _sensitivity_stub(),
                    "type": "float"
                },
            }
        }
    tags["CP"] = cp_block


def run_dervet(json_path):
    result = subprocess.run(
        ["conda", "run", "-n", "dervet-venv", "python", "run_DERVET.py", json_path],
        cwd=BASE_DIR,
        capture_output=True, text=True, timeout=300
    )
    return result.returncode, result.stdout, result.stderr


def extract_results(results_dir, cp_events):
    metrics = {}

    pf_path = os.path.join(results_dir, "pro_forma.csv")
    if os.path.exists(pf_path):
        with open(pf_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if len(rows) >= 2:
                yr1 = rows[1]
                metrics["yearly_net_value"] = float(yr1.get("Yearly Net Value", 0))
                metrics["avoided_demand_charge"] = (
                    float(yr1["Avoided Demand Charge"])
                    if "Avoided Demand Charge" in yr1 else 0
                )
                metrics["da_ets"] = (
                    float(yr1["DA ETS"]) if "DA ETS" in yr1 else 0
                )
                for ev in cp_events:
                    col = f"Avoided CP Charges ({ev['label'].lower()})"
                    key = f"avoided_cp_{ev['id']}"
                    metrics[key] = float(yr1[col]) if col in yr1 else 0

    npv_path = os.path.join(results_dir, "npv.csv")
    if os.path.exists(npv_path):
        with open(npv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                metrics["npv"] = float(row.get("Lifetime Present Value", 0))

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
    print(f"Scenario: {SCENARIO_NAME}")
    print(f"Battery: {BATTERY['power_kw']}kW / {BATTERY['energy_kwh']}kWh")
    print(f"Services: DA={SERVICES['da']}, DCM={SERVICES['dcm']}, "
          f"Retail={SERVICES['retail']}")
    print(f"CP Events: {len(CP_EVENTS)}")
    for ev in CP_EVENTS:
        n_dates = len(ev["dates"].split(","))
        print(f"  {ev['label']}: rate=${ev['rate_monthly']}/kW-mo, "
              f"{n_dates} events, growth={ev['growth']}%")
    print()

    with open(INPUT_JSON) as f:
        base_data = json.load(f)

    data = json.loads(json.dumps(base_data))

    configure_battery(data, BATTERY["power_kw"], BATTERY["energy_kwh"])
    configure_services(data, **SERVICES)
    configure_cp_events(data, CP_EVENTS)

    with open(INPUT_JSON, 'w') as f:
        json.dump(data, f, indent=2)

    print("Running DER-VET...")
    rc, stdout, stderr = run_dervet(INPUT_JSON)

    if rc != 0:
        print(f"FAILED (exit code {rc})")
        print(f"stdout:\n{stdout[-1000:]}")
        print(f"stderr:\n{stderr[-1000:]}")
        return

    print("SUCCESS\n")

    metrics = extract_results(RESULTS_DIR, CP_EVENTS)

    print(f"{'Metric':<35} {'Value':>15}")
    print("-" * 52)
    print(f"{'NPV':.<35} ${metrics.get('npv', 0):>13,.0f}")
    print(f"{'Avoided Demand Charge (yr1)':.<35} ${metrics.get('avoided_demand_charge', 0):>13,.0f}")
    print(f"{'DA Energy Time Shift (yr1)':.<35} ${metrics.get('da_ets', 0):>13,.0f}")
    for ev in CP_EVENTS:
        key = f"avoided_cp_{ev['id']}"
        val = metrics.get(key, 0)
        print(f"{'Avoided CP - ' + ev['label'] + ' (yr1)':.<35} ${val:>13,.0f}")
    print(f"{'Yearly Net Value (yr1)':.<35} ${metrics.get('yearly_net_value', 0):>13,.0f}")
    pb = metrics.get('payback_years', float('inf'))
    pb_str = f"{pb:.1f} years" if pb < 100 else "Never"
    print(f"{'Payback Period':.<35} {pb_str:>15}")

    dest = os.path.join(OUTPUT_DIR, SCENARIO_NAME)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(RESULTS_DIR, dest)
    print(f"\nResults copied to: {dest}")

    summary_path = os.path.join(OUTPUT_DIR, f"{SCENARIO_NAME}_summary.csv")
    metrics["scenario"] = SCENARIO_NAME
    metrics["power_kw"] = BATTERY["power_kw"]
    metrics["energy_kwh"] = BATTERY["energy_kwh"]
    with open(summary_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=metrics.keys())
        writer.writeheader()
        writer.writerow(metrics)
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
