"""Run a single DER-VET scenario and save results under an idempotent name.

This module is called by run_scenarios.py at the repo root.  It:
  1. Deep-copies the base model JSON
  2. Patches battery / service / CP parameters from the scenario dict
  3. Invokes run_DERVET.py via subprocess
  4. Copies the raw results into Results/scenario_comparison/<name>/
  5. Returns a metrics dict extracted from the pro-forma
"""
import json
import subprocess
import shutil
import os
import csv
import copy
import glob


def _sensitivity_stub():
    return {"active": "no", "coupled": "None", "value": "nan"}


def _configure_battery(data, power_kw, energy_kwh):
    batt_keys = data["tags"]["Battery"]
    batt_id = list(batt_keys.keys())[0]
    batt = batt_keys[batt_id]["keys"]
    batt["ch_max_rated"]["opt_value"] = str(power_kw)
    batt["dis_max_rated"]["opt_value"] = str(power_kw)
    batt["ene_max_rated"]["opt_value"] = str(energy_kwh)


def _configure_services(data, da_on, dcm_on, retail_on):
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


def _configure_cp_events(data, cp_events):
    """Write multi-instance CP block, or remove CP entirely if list is empty."""
    tags = data["tags"]
    if not cp_events:
        tags.pop("CP", None)
        return
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
                    "opt_value": str(ev.get("growth", 3)),
                    "sensitivity": _sensitivity_stub(),
                    "type": "float"
                },
            }
        }
    tags["CP"] = cp_block


def _run_dervet(base_dir, json_path, timeout=300):
    result = subprocess.run(
        ["conda", "run", "-n", "dervet-venv", "python", "run_DERVET.py", json_path],
        cwd=base_dir,
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def _extract_metrics(results_dir, cp_events):
    metrics = {}
    rows = []
    pf_path = os.path.join(results_dir, "pro_forma.csv")
    if os.path.exists(pf_path):
        with open(pf_path) as f:
            rows = list(csv.DictReader(f))
            if rows:
                yr0 = rows[0]
                yr_last = rows[-1]
                metrics["year_0"] = int(yr0.get("Year", 0))
                metrics["year_last"] = int(yr_last.get("Year", 0))
                net_0 = float(yr0.get("Yearly Net Value", 0))
                net_last = float(yr_last.get("Yearly Net Value", 0))
                metrics["yearly_net_value"] = net_0
                metrics["yearly_net_value_last"] = net_last
                batt_0 = sum(float(yr0[c]) for c in yr0 if c.startswith("BATTERY:"))
                tax_0 = sum(float(yr0[c]) for c in yr0 if "Tax" in c)
                metrics["gross_bill_savings"] = net_0 - batt_0 - tax_0
                batt_last = sum(float(yr_last[c]) for c in yr_last if c.startswith("BATTERY:"))
                tax_last = sum(float(yr_last[c]) for c in yr_last if "Tax" in c)
                metrics["gross_bill_savings_last"] = net_last - batt_last - tax_last
                metrics["avoided_demand_charge"] = (
                    float(yr0["Avoided Demand Charge"])
                    if "Avoided Demand Charge" in yr0 else 0
                )
                metrics["da_ets"] = (
                    float(yr0["DA ETS"]) if "DA ETS" in yr0 else 0
                )
                for ev in cp_events:
                    col = f"Avoided CP Charges ({ev['label'].lower()})"
                    key = f"avoided_cp_{ev['id']}"
                    metrics[key] = float(yr0[col]) if col in yr0 else 0

    npv_path = os.path.join(results_dir, "npv.csv")
    if os.path.exists(npv_path):
        with open(npv_path) as f:
            for row in csv.DictReader(f):
                metrics["npv"] = float(row.get("Lifetime Present Value", 0))

    gross = metrics.get("gross_bill_savings", 0)
    if gross > 0:
        capex = abs(sum(
            float(rows[0][c]) for c in rows[0]
            if c.startswith("BATTERY:") and "Capital" in c
        )) if rows else 0
        metrics["payback_years"] = capex / gross if capex > 0 else 0
    else:
        metrics["payback_years"] = float("inf")

    return metrics


def run_scenario(scenario, base_dir, input_json, raw_results_dir, output_root):
    """Run one scenario and return (metrics_dict, output_dir) or (None, None) on failure.

    Args:
        scenario: dict with keys name, battery, services, cp_events
        base_dir: repo root path
        input_json: path to the base model_parameters.json to patch
        raw_results_dir: where DER-VET writes its results (gets overwritten each run)
        output_root: parent dir for idempotent output folders
    """
    name = scenario["name"]
    battery = scenario["battery"]
    services = scenario["services"]
    cp_events = scenario.get("cp_events", [])

    print(f"\n{'='*64}")
    print(f"  Scenario: {name}")
    print(f"  Battery:  {battery['power_kw']}kW / {battery['energy_kwh']}kWh")
    svc_str = ", ".join(k.upper() for k, v in services.items() if v)
    print(f"  Services: {svc_str or '(none)'}")
    if cp_events:
        for ev in cp_events:
            n = len(ev["dates"].split(","))
            print(f"  CP: {ev['label']}  rate=${ev['rate_monthly']}/kW-mo  "
                  f"{n} events  growth={ev.get('growth', 3)}%")
    print(f"{'='*64}")

    with open(input_json) as f:
        base_data = json.load(f)
    data = copy.deepcopy(base_data)

    _configure_battery(data, battery["power_kw"], battery["energy_kwh"])
    _configure_services(data, services.get("da", False),
                        services.get("dcm", False),
                        services.get("retail", False))
    _configure_cp_events(data, cp_events)

    with open(input_json, "w") as f:
        json.dump(data, f, indent=2)

    # Remove stale cp_event_detail files from previous runs
    for stale in glob.glob(os.path.join(raw_results_dir, "cp_event_detail*.csv")):
        os.remove(stale)

    print("  Running DER-VET ...")
    rc, stdout, stderr = _run_dervet(base_dir, input_json)

    # Restore the original JSON so the next run starts clean
    with open(input_json, "w") as f:
        json.dump(base_data, f, indent=2)

    if rc != 0:
        print(f"  FAILED (exit {rc})")
        print(f"  stderr (last 500 chars): {stderr[-500:]}")
        return None, None

    dest = os.path.join(output_root, name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(raw_results_dir, dest)

    metrics = _extract_metrics(dest, cp_events)
    metrics["scenario"] = name
    metrics["power_kw"] = battery["power_kw"]
    metrics["energy_kwh"] = battery["energy_kwh"]

    y0 = metrics.get("year_0", "?")
    y_last = metrics.get("year_last", "?")
    print(f"  Gross bill savings  ({y0}): ${metrics.get('gross_bill_savings', 0):>12,.0f}")
    print(f"  Gross bill savings  ({y_last}): ${metrics.get('gross_bill_savings_last', 0):>12,.0f}")
    print(f"  Results -> {dest}")

    return metrics, dest
