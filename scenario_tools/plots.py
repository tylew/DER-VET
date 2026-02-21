"""Generate visualization plots for completed DER-VET scenario results.

Plot types:
  - Full-year load vs battery profile
  - 48-hour windows around each CP event
  - Best non-CP arbitrage day (when DA is active)
  - Best non-CP peak-shaving day (when DCM is active)

Called by run_scenarios.py after each scenario completes.
"""
import os
import glob
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_timeseries(results_dir):
    return pd.read_csv(
        os.path.join(results_dir, "timeseries_results.csv"),
        index_col=0, parse_dates=True,
    )


def _load_da_price(input_dir):
    ts_path = os.path.join(input_dir, "timeseries.csv")
    if not os.path.exists(ts_path):
        return None
    da_ts = pd.read_csv(ts_path, index_col=0, parse_dates=True)
    if "DA Price ($/kWh)" in da_ts.columns:
        return da_ts["DA Price ($/kWh)"] * 1000  # convert to $/MWh
    return None


def _cp_dates_from_details(results_dir):
    """Return set of dates that are CP event days (plus the day before)."""
    cp_dates = set()
    for path in glob.glob(os.path.join(results_dir, "cp_event_detail*.csv")):
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            d = pd.Timestamp(row["Date"]).date()
            cp_dates.add(d)
            cp_dates.add((pd.Timestamp(d) - timedelta(days=1)).date())
    return cp_dates


def _load_cp_events(results_dir):
    """Load all CP event detail rows across all instance CSVs."""
    events = []
    for path in sorted(glob.glob(os.path.join(results_dir, "cp_event_detail*.csv"))):
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            events.append({
                "type": row["Type"],
                "date": pd.Timestamp(row["Date"]),
                "he": int(row["Hour Ending"]),
                "orig": row["Original Load (kW)"],
                "opt": row["Optimized Load (kW)"],
                "reduction": row["Reduction (kW)"],
            })
    return events


_EVENT_COLORS = [
    "#DC2626", "#7C3AED", "#0891B2", "#D97706", "#059669",
    "#DB2777", "#4F46E5", "#65A30D",
]


def _event_color(ev_type, seen_types):
    """Assign a stable color per unique CP event type."""
    if ev_type not in seen_types:
        seen_types[ev_type] = _EVENT_COLORS[len(seen_types) % len(_EVENT_COLORS)]
    return seen_types[ev_type]


def _standard_day_plot(ts, da_price, window_start, window_end,
                       title, plot_path, annotations=None):
    """Shared 4-panel day-window plot (load, battery, SOC, DA price)."""
    w = ts.loc[window_start:window_end]
    if w.empty:
        return

    w_load = w["LOAD: Site Load Original Load (kW)"]
    w_net = w["Net Load (kW)"]
    w_chg = w["BATTERY: bess 1 Charge (kW)"]
    w_dis = w["BATTERY: bess 1 Discharge (kW)"]
    w_soc = w["BATTERY: bess 1 SOC (%)"]

    has_price = da_price is not None
    n_panels = 4 if has_price else 3
    ratios = [3, 2, 1.5, 1.5] if has_price else [3, 2, 1.5]
    fig, axes = plt.subplots(
        n_panels, 1, figsize=(16, 13 if has_price else 10),
        sharex=True, gridspec_kw={"height_ratios": ratios},
    )

    # Panel 1: load
    axes[0].plot(w_load.index, w_load.values, color="#888888",
                 linewidth=1.5, label="Original Load", zorder=3)
    axes[0].plot(w_net.index, w_net.values, color="#2563EB",
                 linewidth=1.5, label="Net Load (after battery)", zorder=4)
    axes[0].fill_between(w_load.index, w_net.values, w_load.values,
                         where=w_load.values > w_net.values,
                         color="#22C55E", alpha=0.25,
                         label="Peak Shaved (discharge)",
                         interpolate=True, zorder=2)
    axes[0].fill_between(w_load.index, w_load.values, w_net.values,
                         where=w_net.values > w_load.values,
                         color="#EF4444", alpha=0.25,
                         label="Added Load (charging)",
                         interpolate=True, zorder=2)

    if annotations:
        annotations(axes, w)

    axes[0].set_ylabel("Load (kW)")
    axes[0].legend(loc="upper left", fontsize=8)
    axes[0].set_title(title)
    axes[0].grid(True, alpha=0.3)

    # Panel 2: battery power
    axes[1].bar(w_dis.index, w_dis.values, width=0.01, color="#22C55E",
                alpha=0.7, label="Discharging")
    axes[1].bar(w_chg.index, -w_chg.values, width=0.01, color="#EF4444",
                alpha=0.7, label="Charging")
    axes[1].axhline(0, color="black", linewidth=0.5)
    axes[1].set_ylabel("Battery Power (kW)")
    axes[1].legend(loc="upper left", fontsize=8)
    axes[1].grid(True, alpha=0.3)

    # Panel 3: SOC
    axes[2].plot(w_soc.index, w_soc.values, color="#8B5CF6", linewidth=1.5)
    axes[2].fill_between(w_soc.index, 0, w_soc.values, color="#8B5CF6",
                         alpha=0.15)
    axes[2].set_ylabel("SOC (%)")
    axes[2].set_ylim(-5, 105)
    axes[2].grid(True, alpha=0.3)

    # Panel 4: DA price
    last_ax = axes[2]
    if has_price:
        w_price = da_price.loc[window_start:window_end]
        axes[3].plot(w_price.index, w_price.values, color="#F59E0B",
                     linewidth=1.5)
        axes[3].fill_between(w_price.index, 0, w_price.values,
                             color="#F59E0B", alpha=0.15)
        axes[3].set_ylabel("DA Price ($/MWh)")
        axes[3].grid(True, alpha=0.3)
        last_ax = axes[3]

    last_ax.set_xlabel("Date / Time")
    last_ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    last_ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.setp(last_ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

    plt.tight_layout()
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    # print(f"    Saved: {plot_path}")


# ---------------------------------------------------------------------------
# Public plot generators
# ---------------------------------------------------------------------------

def plot_full_year(ts, scenario_name, plot_dir):
    """Full-year load, battery power, and SOC."""
    site_load = ts["LOAD: Site Load Original Load (kW)"]
    net_load = ts["Net Load (kW)"]
    batt_power = ts["BATTERY: bess 1 Power (kW)"]
    soc = ts["BATTERY: bess 1 SOC (%)"]

    cp_cols = [c for c in ts.columns if c.startswith("CP-") and c.endswith("Indicator")]
    cp_combined = ts[cp_cols].max(axis=1) if cp_cols else None

    fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)

    axes[0].plot(site_load.index, site_load.values, color="#888888",
                 linewidth=0.3, alpha=0.7, label="Original Load")
    axes[0].plot(net_load.index, net_load.values, color="#2563EB",
                 linewidth=0.3, alpha=0.8, label="Net Load (after battery)")
    if cp_combined is not None:
        cp_mask = cp_combined > 0
        cp_times = site_load.index[cp_mask]
        if len(cp_times):
            axes[0].scatter(cp_times, site_load.loc[cp_times], color="red",
                            s=30, zorder=5, label="CP Events")
    axes[0].set_ylabel("Load (kW)")
    axes[0].legend(loc="upper right")
    axes[0].set_title(f"{scenario_name} -- Full Year Load Profile")
    axes[0].grid(True, alpha=0.3)

    discharge = batt_power.clip(lower=0)
    charge = batt_power.clip(upper=0)
    axes[1].fill_between(batt_power.index, 0, discharge.values,
                         color="#22C55E", alpha=0.5, label="Discharging")
    axes[1].fill_between(batt_power.index, 0, charge.values,
                         color="#EF4444", alpha=0.5, label="Charging")
    axes[1].set_ylabel("Battery Power (kW)")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(soc.index, soc.values, color="#8B5CF6", linewidth=0.4)
    axes[2].set_ylabel("SOC (%)")
    axes[2].set_ylim(-5, 105)
    axes[2].set_xlabel("Date")
    axes[2].grid(True, alpha=0.3)
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[2].xaxis.set_major_locator(mdates.MonthLocator())

    plt.tight_layout()
    path = os.path.join(plot_dir, "full_year_load_vs_battery.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    # print(f"    Saved: {path}")


def plot_cp_windows(ts, da_price, results_dir, scenario_name, plot_dir):
    """48-hour windows around each CP event date."""
    cp_events = _load_cp_events(results_dir)
    if not cp_events:
        return

    unique_dates = sorted(set(e["date"].date() for e in cp_events))
    color_map = {}

    for cp_date in unique_dates:
        window_start = pd.Timestamp(cp_date) - timedelta(hours=24)
        window_end = pd.Timestamp(cp_date) + timedelta(hours=24)
        w = ts.loc[window_start:window_end]
        if w.empty:
            continue

        window_events = [
            e for e in cp_events
            if window_start <= e["date"] + timedelta(hours=e["he"] - 1) <= window_end
        ]

        def _annotate_cp(axes, w, _events=window_events, _cm=color_map):
            annotated = set()
            for i, ev in enumerate(sorted(_events, key=lambda e: (e["date"], e["he"]))):
                color = _event_color(ev["type"], _cm)
                hb = ev["he"] - 1
                ev_start = pd.Timestamp(ev["date"].date()).replace(hour=hb)
                ev_end = ev_start + timedelta(hours=1)
                lbl = ev["type"] if ev["type"] not in annotated else None
                for ax in axes:
                    ax.axvspan(ev_start, ev_end, color=color, alpha=0.12,
                               label=lbl if ax is axes[0] else None)
                annotated.add(ev["type"])
                y_off = 40 if i % 2 == 0 else 15
                axes[0].annotate(
                    f"{ev['type']}\nHE{ev['he']}  {ev['date'].strftime('%m/%d')}\n"
                    f"{ev['reduction']:.0f} kW shaved",
                    xy=(ev_start + timedelta(minutes=30), ev["opt"]),
                    xytext=(0, y_off), textcoords="offset points",
                    fontsize=7.5, ha="center", va="bottom",
                    color=color, fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=color, lw=0.8),
                )
            axes[0].axvline(pd.Timestamp(cp_date), color="gray",
                            linestyle="--", alpha=0.5, label="Event Day")

        evt_summary = ", ".join(sorted(set(e["type"] for e in window_events)))
        title = (f"{scenario_name} -- 48h Window Around {cp_date}  "
                 f"({len(window_events)} events: {evt_summary})")
        date_str = pd.Timestamp(cp_date).strftime("%Y%m%d")
        path = os.path.join(plot_dir, f"cp_event_{date_str}.png")

        _standard_day_plot(ts, da_price, window_start, window_end,
                           title, path, annotations=_annotate_cp)


def plot_arbitrage_day(ts, da_price, results_dir, scenario_name, plot_dir,
                       target_date=None):
    """Best non-CP day with highest total battery throughput (arbitrage)."""
    if da_price is None:
        return

    batt = ts["BATTERY: bess 1 Power (kW)"]

    if target_date is None:
        cp_dates = _cp_dates_from_details(results_dir)
        daily_throughput = batt.abs().groupby(batt.index.date).sum()
        non_cp = daily_throughput[~daily_throughput.index.isin(cp_dates)]
        if non_cp.empty:
            return
        target_date = pd.Timestamp(non_cp.idxmax())
    else:
        target_date = pd.Timestamp(target_date)

    window_start = target_date - timedelta(hours=6)
    window_end = target_date + timedelta(hours=30)

    def _annotate_dc(axes, w):
        if 6 <= target_date.month <= 9:
            dc_start = target_date.replace(hour=8)
            dc_end = target_date.replace(hour=22)
            axes[0].axvspan(dc_start, dc_end, color="#FCD34D", alpha=0.08, zorder=1)
            axes[0].text(dc_start + timedelta(hours=0.5),
                         w["LOAD: Site Load Original Load (kW)"].max() * 0.98,
                         "Summer Demand Charge Window (8am-10pm)",
                         fontsize=7, color="#B45309", fontstyle="italic", va="top")

    title = (f"{scenario_name} -- Best Arbitrage Day: "
             f"{target_date.strftime('%b %d, %Y')}")
    date_str = target_date.strftime("%Y%m%d")
    path = os.path.join(plot_dir, f"arbitrage_day_{date_str}.png")

    _standard_day_plot(ts, da_price, window_start, window_end,
                       title, path, annotations=_annotate_dc)


def plot_peak_shaving_day(ts, da_price, results_dir, scenario_name, plot_dir,
                          target_date=None):
    """Best non-CP day with highest discharge during demand-charge window.

    Selects the day (excluding CP days) where the battery discharged the most
    during the 8am-10pm period -- a proxy for peak-shaving (DCM) activity.
    """
    batt_dis = ts["BATTERY: bess 1 Discharge (kW)"]

    if target_date is None:
        cp_dates = _cp_dates_from_details(results_dir)

        dc_window = batt_dis.between_time("08:00", "21:45")
        daily_dc_discharge = dc_window.groupby(dc_window.index.date).sum()
        non_cp = daily_dc_discharge[~daily_dc_discharge.index.isin(cp_dates)]
        if non_cp.empty or non_cp.max() == 0:
            return
        target_date = pd.Timestamp(non_cp.idxmax())
    else:
        target_date = pd.Timestamp(target_date)

    window_start = target_date - timedelta(hours=6)
    window_end = target_date + timedelta(hours=30)

    def _annotate_dc(axes, w):
        dc_start = target_date.replace(hour=8)
        dc_end = target_date.replace(hour=22)
        axes[0].axvspan(dc_start, dc_end, color="#FCD34D", alpha=0.08, zorder=1)
        axes[0].text(dc_start + timedelta(hours=0.5),
                     w["LOAD: Site Load Original Load (kW)"].max() * 0.98,
                     "Demand Charge Window (8am-10pm)",
                     fontsize=7, color="#B45309", fontstyle="italic", va="top")

    title = (f"{scenario_name} -- Best Peak-Shaving Day: "
             f"{target_date.strftime('%b %d, %Y')}")
    date_str = target_date.strftime("%Y%m%d")
    path = os.path.join(plot_dir, f"peak_shaving_day_{date_str}.png")

    _standard_day_plot(ts, da_price, window_start, window_end,
                       title, path, annotations=_annotate_dc)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_all_plots(scenario, results_dir, input_dir):
    """Generate all relevant plots for a completed scenario.

    Args:
        scenario: dict with keys name, services, cp_events, etc.
        results_dir: path to this scenario's copied results
        input_dir: path to the facility input directory (for DA prices)
    """
    name = scenario["name"]
    services = scenario["services"]
    cp_events = scenario.get("cp_events", [])

    plot_dir = os.path.join(results_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    print(f"  Generating plots for {name} ...")

    ts = _load_timeseries(results_dir)
    da_price = _load_da_price(input_dir)

    plot_full_year(ts, name, plot_dir)

    if cp_events:
        plot_cp_windows(ts, da_price, results_dir, name, plot_dir)

    if services.get("da"):
        plot_arbitrage_day(ts, da_price, results_dir, name, plot_dir)

    if services.get("dcm"):
        plot_peak_shaving_day(ts, da_price, results_dir, name, plot_dir)

    print(f"  Complete.")
