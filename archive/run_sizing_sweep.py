"""Sweep battery sizes and generate visualizations for facility_70."""
import json
import subprocess
import shutil
import os
import csv

BASE_DIR = "/Users/fsl/Documents/GitHub/DER-VET"
INPUT_JSON = os.path.join(BASE_DIR, "Results/facility_70/inputs/model_parameters.json")
RESULTS_DIR = os.path.join(BASE_DIR, "Results/facility_70/results")
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
    """Toggle CP value stream and set rates/dates (multi-instance format)."""
    tags = data["tags"]
    sens = {"active": "no", "coupled": "None", "value": "nan"}
    active = "yes" if cp_on else "no"
    tags["CP"] = {
        "pjm_5cp": {
            "active": active,
            "keys": {
                "rate_monthly": {"opt_value": str(capacity_rate), "sensitivity": dict(sens), "type": "float"},
                "cp_dates": {"opt_value": pjm_5cp_dates, "sensitivity": dict(sens), "type": "string"},
                "label": {"opt_value": "PJM 5CP", "sensitivity": dict(sens), "type": "string"},
                "growth": {"opt_value": str(growth), "sensitivity": dict(sens), "type": "float"},
            }
        },
        "pseg_1cp": {
            "active": active,
            "keys": {
                "rate_monthly": {"opt_value": str(transmission_rate), "sensitivity": dict(sens), "type": "float"},
                "cp_dates": {"opt_value": utility_1cp_dates, "sensitivity": dict(sens), "type": "string"},
                "label": {"opt_value": "PSEG 1CP", "sensitivity": dict(sens), "type": "string"},
                "growth": {"opt_value": str(growth), "sensitivity": dict(sens), "type": "float"},
            }
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
                metrics["avoided_cp_capacity"] = float(yr1.get("Avoided CP Charges (pjm 5cp)", 0)) if "Avoided CP Charges (pjm 5cp)" in yr1 else 0
                metrics["avoided_cp_transmission"] = float(yr1.get("Avoided CP Charges (pseg 1cp)", 0)) if "Avoided CP Charges (pseg 1cp)" in yr1 else 0
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


def generate_plots(results_dir, output_dir, input_dir=None):
    """Generate load vs battery plots from a completed DER-VET run."""
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import timedelta

    ts = pd.read_csv(os.path.join(results_dir, 'timeseries_results.csv'),
                      index_col=0, parse_dates=True)

    da_price = None
    if input_dir:
        da_ts = pd.read_csv(os.path.join(input_dir, 'timeseries.csv'),
                            index_col=0, parse_dates=True)
        if 'DA Price ($/kWh)' in da_ts.columns:
            da_price = da_ts['DA Price ($/kWh)'] * 1000

    site_load = ts['LOAD: Site Load Original Load (kW)']
    net_load = ts['Net Load (kW)']
    batt_power = ts['BATTERY: bess 1 Power (kW)']
    soc = ts['BATTERY: bess 1 SOC (%)']
    cp_indicator_cols = [c for c in ts.columns if c.startswith('CP-') and c.endswith('Indicator')]
    cp_combined = None
    if cp_indicator_cols:
        cp_combined = ts[cp_indicator_cols].max(axis=1)

    plot_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plot_dir, exist_ok=True)

    # --- Full-year load vs battery ---
    fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)

    axes[0].plot(site_load.index, site_load.values, color='#888888',
                 linewidth=0.3, alpha=0.7, label='Original Load')
    axes[0].plot(net_load.index, net_load.values, color='#2563EB',
                 linewidth=0.3, alpha=0.8, label='Net Load (after battery)')
    if cp_combined is not None:
        cp_mask = cp_combined > 0
        cp_times = site_load.index[cp_mask]
        axes[0].scatter(cp_times, site_load.loc[cp_times], color='red',
                        s=30, zorder=5, label='CP Events')
    axes[0].set_ylabel('Load (kW)')
    axes[0].legend(loc='upper right')
    axes[0].set_title('Facility 70 -- Full Year Load Profile (DA + DCM + CP, 250kW/500kWh)')
    axes[0].grid(True, alpha=0.3)

    discharge = batt_power.clip(lower=0)
    charge = batt_power.clip(upper=0)
    axes[1].fill_between(batt_power.index, 0, discharge.values,
                         color='#22C55E', alpha=0.5, label='Discharging')
    axes[1].fill_between(batt_power.index, 0, charge.values,
                         color='#EF4444', alpha=0.5, label='Charging')
    axes[1].set_ylabel('Battery Power (kW)')
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(soc.index, soc.values, color='#8B5CF6', linewidth=0.4)
    axes[2].set_ylabel('SOC (%)')
    axes[2].set_ylim(-5, 105)
    axes[2].set_xlabel('Date')
    axes[2].grid(True, alpha=0.3)
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    axes[2].xaxis.set_major_locator(mdates.MonthLocator())

    plt.tight_layout()
    path = os.path.join(plot_dir, 'full_year_load_vs_battery.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")

    # --- 48-hour CP event windows ---
    cp_events = []
    import glob as _glob
    for cp_detail_path in sorted(_glob.glob(os.path.join(results_dir, 'cp_event_detail*.csv'))):
        cp_df = pd.read_csv(cp_detail_path)
        for _, row in cp_df.iterrows():
            cp_events.append({
                'type': row['Type'],
                'date': pd.Timestamp(row['Date']),
                'he': int(row['Hour Ending']),
                'orig': row['Original Load (kW)'],
                'opt': row['Optimized Load (kW)'],
                'reduction': row['Reduction (kW)'],
            })

    unique_dates = sorted(set(e['date'].date() for e in cp_events))

    EVENT_STYLES = {
        '5CP': {'color': '#DC2626', 'label': '5CP (PJM)'},
        '1CP': {'color': '#7C3AED', 'label': '1CP (Utility)'},
    }

    def _event_style(ev_type):
        if '5CP' in ev_type:
            return EVENT_STYLES['5CP']
        return EVENT_STYLES['1CP']

    has_price = da_price is not None

    for cp_date in unique_dates:
        window_start = pd.Timestamp(cp_date) - timedelta(hours=24)
        window_end = pd.Timestamp(cp_date) + timedelta(hours=24)
        window = ts.loc[window_start:window_end]
        if window.empty:
            continue

        window_events = [e for e in cp_events
                         if window_start <= e['date'] + timedelta(hours=e['he']-1)
                                          <= window_end]

        w_load = window['LOAD: Site Load Original Load (kW)']
        w_net = window['Net Load (kW)']
        w_chg = window['BATTERY: bess 1 Charge (kW)']
        w_dis = window['BATTERY: bess 1 Discharge (kW)']
        w_soc = window['BATTERY: bess 1 SOC (%)']

        n_panels = 4 if has_price else 3
        ratios = [3, 2, 1.5, 1.5] if has_price else [3, 2, 1.5]
        fig, axes = plt.subplots(n_panels, 1, figsize=(16, 13 if has_price else 10),
                                  sharex=True, gridspec_kw={'height_ratios': ratios})

        # Panel 1: Load with fill-between shading
        axes[0].plot(w_load.index, w_load.values, color='#888888',
                     linewidth=1.5, label='Original Load', zorder=3)
        axes[0].plot(w_net.index, w_net.values, color='#2563EB',
                     linewidth=1.5, label='Net Load (after battery)', zorder=4)
        axes[0].fill_between(w_load.index, w_net.values, w_load.values,
                             where=w_load.values > w_net.values,
                             color='#22C55E', alpha=0.25,
                             label='Peak Shaved (discharge)',
                             interpolate=True, zorder=2)
        axes[0].fill_between(w_load.index, w_load.values, w_net.values,
                             where=w_net.values > w_load.values,
                             color='#EF4444', alpha=0.25,
                             label='Added Load (charging)',
                             interpolate=True, zorder=2)

        annotated_types = set()
        for i, ev in enumerate(sorted(window_events,
                                       key=lambda e: (e['date'], e['he']))):
            style = _event_style(ev['type'])
            hb = ev['he'] - 1
            ev_start = pd.Timestamp(ev['date'].date()).replace(hour=hb, minute=0)
            ev_end = ev_start + timedelta(hours=1)
            span_label = style['label'] if style['label'] not in annotated_types else None
            for ax in axes:
                ax.axvspan(ev_start, ev_end, color=style['color'],
                           alpha=0.12, label=span_label if ax is axes[0] else None)
            annotated_types.add(style['label'])

            y_offset = 40 if (i % 2 == 0) else 15
            axes[0].annotate(
                f"{ev['type']}\nHE{ev['he']}  {ev['date'].strftime('%m/%d')}\n"
                f"{ev['reduction']:.0f} kW shaved",
                xy=(ev_start + timedelta(minutes=30), ev['opt']),
                xytext=(0, y_offset), textcoords='offset points',
                fontsize=7.5, ha='center', va='bottom',
                color=style['color'], fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=style['color'],
                                lw=0.8),
            )

        axes[0].axvline(pd.Timestamp(cp_date), color='gray',
                        linestyle='--', alpha=0.5, label='Event Day')
        axes[0].set_ylabel('Load (kW)')
        axes[0].legend(loc='upper left', fontsize=8)
        n_events = len(window_events)
        event_summary = ', '.join(
            sorted(set(f"{e['type']}" for e in window_events)))
        axes[0].set_title(
            f'Facility 70 -- 48h Window Around {cp_date}  '
            f'({n_events} CP events: {event_summary})')
        axes[0].grid(True, alpha=0.3)

        # Panel 2: Battery power as discrete bars
        axes[1].bar(w_dis.index, w_dis.values, width=0.01, color='#22C55E',
                    alpha=0.7, label='Discharging')
        axes[1].bar(w_chg.index, -w_chg.values, width=0.01, color='#EF4444',
                    alpha=0.7, label='Charging')
        axes[1].axhline(0, color='black', linewidth=0.5)
        axes[1].set_ylabel('Battery Power (kW)')
        axes[1].legend(loc='upper left', fontsize=8)
        axes[1].grid(True, alpha=0.3)

        # Panel 3: SOC with fill
        axes[2].plot(w_soc.index, w_soc.values, color='#8B5CF6',
                     linewidth=1.5)
        axes[2].fill_between(w_soc.index, 0, w_soc.values, color='#8B5CF6',
                             alpha=0.15)
        axes[2].set_ylabel('SOC (%)')
        axes[2].set_ylim(-5, 105)
        axes[2].grid(True, alpha=0.3)

        # Panel 4: DA Price (if available)
        last_ax = axes[2]
        if has_price:
            w_price = da_price.loc[window_start:window_end]
            axes[3].plot(w_price.index, w_price.values, color='#F59E0B',
                         linewidth=1.5)
            axes[3].fill_between(w_price.index, 0, w_price.values,
                                 color='#F59E0B', alpha=0.15)
            axes[3].set_ylabel('DA Price ($/MWh)')
            axes[3].grid(True, alpha=0.3)
            last_ax = axes[3]

        last_ax.set_xlabel('Date / Time')
        last_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        last_ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.setp(last_ax.xaxis.get_majorticklabels(), rotation=30, ha='right')

        plt.tight_layout()
        date_str = cp_date.strftime('%Y%m%d')
        path = os.path.join(plot_dir, f'cp_event_{date_str}.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {path}")


def generate_arbitrage_day_plot(results_dir, input_dir, output_dir,
                                target_date=None):
    """Generate a detailed plot of the best non-CP dispatch day.

    If target_date is None, automatically selects the non-CP day with the
    highest battery throughput.
    """
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import timedelta

    ts = pd.read_csv(os.path.join(results_dir, 'timeseries_results.csv'),
                     index_col=0, parse_dates=True)
    da_ts = pd.read_csv(os.path.join(input_dir, 'timeseries.csv'),
                        index_col=0, parse_dates=True)

    batt = ts['BATTERY: bess 1 Power (kW)']

    if target_date is None:
        cp_dates = set()
        import glob as _glob2
        for cp_detail_path in _glob2.glob(os.path.join(results_dir, 'cp_event_detail*.csv')):
            cp_df = pd.read_csv(cp_detail_path)
            for _, row in cp_df.iterrows():
                d = pd.Timestamp(row['Date']).date()
                cp_dates.add(d)
                cp_dates.add(
                    (pd.Timestamp(d) - timedelta(days=1)).date())

        daily_throughput = batt.abs().groupby(batt.index.date).sum()
        non_cp = daily_throughput[~daily_throughput.index.isin(cp_dates)]
        target_date = pd.Timestamp(non_cp.idxmax())
    else:
        target_date = pd.Timestamp(target_date)

    print(f"  Arbitrage day: {target_date.date()}")

    window_start = target_date - timedelta(hours=6)
    window_end = target_date + timedelta(hours=30)
    w = ts.loc[window_start:window_end]
    w_da = da_ts.loc[window_start:window_end]

    w_load = w['LOAD: Site Load Original Load (kW)']
    w_net = w['Net Load (kW)']
    w_chg = w['BATTERY: bess 1 Charge (kW)']
    w_dis = w['BATTERY: bess 1 Discharge (kW)']
    w_soc = w['BATTERY: bess 1 SOC (%)']
    w_da_price = w_da['DA Price ($/kWh)'] * 1000

    fig, axes = plt.subplots(4, 1, figsize=(16, 13), sharex=True,
                              gridspec_kw={'height_ratios': [3, 2, 1.5, 1.5]})

    axes[0].plot(w_load.index, w_load.values, color='#888888',
                 linewidth=1.5, label='Original Load', zorder=3)
    axes[0].plot(w_net.index, w_net.values, color='#2563EB',
                 linewidth=1.5, label='Net Load (after battery)', zorder=4)
    axes[0].fill_between(w_load.index, w_net.values, w_load.values,
                         where=w_load.values > w_net.values,
                         color='#22C55E', alpha=0.25,
                         label='Peak Shaved (discharge)',
                         interpolate=True, zorder=2)
    axes[0].fill_between(w_load.index, w_load.values, w_net.values,
                         where=w_net.values > w_load.values,
                         color='#EF4444', alpha=0.25,
                         label='Added Load (charging)',
                         interpolate=True, zorder=2)

    dc_start = target_date.replace(hour=8, minute=0)
    dc_end = target_date.replace(hour=22, minute=0)
    if target_date.month >= 6 and target_date.month <= 9:
        axes[0].axvspan(dc_start, dc_end, color='#FCD34D', alpha=0.08,
                        zorder=1)
        axes[0].text(dc_start + timedelta(hours=0.5),
                     w_load.max() * 0.98,
                     'Summer Demand Charge Window (8am-10pm)',
                     fontsize=7, color='#B45309', fontstyle='italic',
                     va='top')

    axes[0].set_ylabel('Load (kW)')
    axes[0].legend(loc='upper left', fontsize=8)
    axes[0].set_title(
        f'Facility 70 -- Best Non-CP Dispatch Day: '
        f'{target_date.strftime("%b %d, %Y")}\n'
        f'(DA + DCM + CP, 250kW/500kWh)')
    axes[0].grid(True, alpha=0.3)

    axes[1].bar(w_dis.index, w_dis.values, width=0.01, color='#22C55E',
                alpha=0.7, label='Discharging')
    axes[1].bar(w_chg.index, -w_chg.values, width=0.01, color='#EF4444',
                alpha=0.7, label='Charging')
    axes[1].axhline(0, color='black', linewidth=0.5)
    axes[1].set_ylabel('Battery Power (kW)')
    axes[1].legend(loc='upper left', fontsize=8)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(w_soc.index, w_soc.values, color='#8B5CF6', linewidth=1.5)
    axes[2].fill_between(w_soc.index, 0, w_soc.values, color='#8B5CF6',
                         alpha=0.15)
    axes[2].set_ylabel('SOC (%)')
    axes[2].set_ylim(-5, 105)
    axes[2].grid(True, alpha=0.3)

    axes[3].plot(w_da_price.index, w_da_price.values, color='#F59E0B',
                 linewidth=1.5)
    axes[3].fill_between(w_da_price.index, 0, w_da_price.values,
                         color='#F59E0B', alpha=0.15)
    axes[3].set_ylabel('DA Price ($/MWh)')
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlabel('Date / Time')
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    axes[3].xaxis.set_major_locator(mdates.HourLocator(interval=3))
    plt.setp(axes[3].xaxis.get_majorticklabels(), rotation=30, ha='right')

    plt.tight_layout()
    plot_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plot_dir, exist_ok=True)
    date_str = target_date.strftime('%Y%m%d')
    path = os.path.join(plot_dir, f'arbitrage_day_{date_str}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")


INPUT_DIR = os.path.join(BASE_DIR, "Results/facility_70/inputs")

if __name__ == "__main__":
    main()
    print("\nGenerating plots from latest results...")
    generate_plots(RESULTS_DIR, OUTPUT_DIR, INPUT_DIR)
    generate_arbitrage_day_plot(RESULTS_DIR, INPUT_DIR, OUTPUT_DIR)
