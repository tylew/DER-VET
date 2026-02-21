# Commit Review Report
**Branch:** `feat/PSEG-TX-5CP`
**Date:** 2026-02-20
**Commits Reviewed:** Last 4 (1b64ffa → fcf04e8)

---

## Summary Table

| # | Hash | Date | Message | Risk |
|---|------|------|---------|------|
| 1 | `1b64ffa` | 2026-02-20 | Update facility 70 results and model parameters | Medium |
| 2 | `7f050ec` | 2026-02-19 | Add Facility XX70 as example | Low |
| 3 | `97b156b` | 2026-02-19 | Add Coincident Peak (CP) value stream | High |
| 4 | `fcf04e8` | 2026-02-18 | Add LP-first solve strategy for ESS sizing | High |

---

## Commit 4 — `fcf04e8` · Add LP-first solve strategy for ESS sizing

### Files Changed
| File | Change Type |
|------|-------------|
| `storagevet/storagevet/Scenario.py` | Modified — new methods, solver options |
| `dervet/MicrogridScenario.py` | Modified — optimization loop replaced |
| `.gitignore` | Minor — added `.DS_Store` |

### Logic Changes

#### `storagevet/storagevet/Scenario.py`

**New methods added:**

- `_toggle_ess_binary(enable)` — Iterates `poi.active_ders`, saves and sets `incl_binary` on any DER that has this attribute. Returns a dict of original values.
- `_restore_ess_binary(original_flags)` — Restores `incl_binary` values saved by the above.
- `_has_simultaneous_charge_discharge(threshold=0.1)` — Inspects `variables_dict['ch']` and `variables_dict['dis']` on each DER post-solve; returns `True` if any timestep has both charge and discharge above the threshold (0.1 kW).
- `_solve_with_lp_first(opt_period, ...)` — Coordinator method:
  1. If `self.incl_binary` is `False`, skips LP-first and solves normally.
  2. Otherwise: disables binaries → solves LP → checks for simultaneous ch/dis → if clean, returns LP result directly.
  3. If simultaneous ch/dis detected: restores binaries → re-solves as MIP.
- `_solver_options(solver_name)` — Static method that returns `{'glpk': {'tm_lim': 300000, 'mip_gap': 0.01}}` for `GLPK_MI`, empty dict otherwise.
- Added class-level constants: `MIP_TIME_LIMIT_MS = 300_000` (5 min), `MIP_GAP_TOLERANCE = 0.01` (1%).

**Modified:**
- `solve_optimization()` — Now calls `self._solver_options(solver_name)` and passes result as `**solver_opts` to `prob.solve(...)`. Applied in both the primary solver call and the fallback retry loop.
- `optimize_problem_loop()` — The per-window setup+solve block was replaced with a single call to `_solve_with_lp_first(opt_period)`. Commented-out debug prints were removed.

#### `dervet/MicrogridScenario.py`

**Modified:**
- `optimize_problem_loop()` — The inline `set_up_optimization` + `solve_optimization` call sequence was replaced with a single `_solve_with_lp_first(...)` call that also passes `annuity_scalar`, `ignore_der_costs`, and `force_glpk_mi`.
- Removed several commented-out debug `print()` blocks that were left from prior development.
- Docstring updated to document LP-first behavior.

**Behavioral change:** Previously, all optimization windows were always solved as MIP (if `incl_binary` was set). Now, the LP relaxation is attempted first per window, and MIP is only used when needed. **The optimization outcome should be equivalent or better in quality; the primary risk is that the simultaneous-charge/discharge detector may miss edge cases where the LP result is technically infeasible under binary constraints.**

**Solver safeguard:** GLPK_MI now has a hard 5-minute wall-clock cap and 1% optimality gap, preventing runaway solves. This was not present before.

### Potential Concerns
- The `_has_simultaneous_charge_discharge` check uses a 0.1 kW threshold. If battery capacity is very small, legitimate dispatch could be suppressed by the threshold — but this is unlikely in practice.
- The LP-first path calls `set_up_optimization` twice per MIP escalation (once for LP, once for MIP). This is correct but increases overhead when MIP is needed.
- `solve_optimization()` signature now returns the same values but the caller in `_solve_with_lp_first` wraps the return as a 4-tuple `(cvx_problem, obj_expressions, cvx_error_msg, sub_index)` — this is a new return shape compared to the old 3-tuple. Both callers (`Scenario.optimize_problem_loop` and `MicrogridScenario.optimize_problem_loop`) were updated consistently.

---

## Commit 3 — `97b156b` · Add Coincident Peak (CP) value stream

### Files Changed
| File | Change Type |
|------|-------------|
| `storagevet/storagevet/ValueStreams/CoincidentPeakShaving.py` | **New file** |
| `storagevet/storagevet/ValueStreams/cp_registry.py` | **New file** |
| `storagevet/storagevet/schema.json` | Modified — CP service block added |
| `dervet/Schema.json` | Modified — CP service block added |
| `storagevet/storagevet/Params.py` | Modified — CP parsed and enriched |
| `storagevet/storagevet/Scenario.py` | Modified — CP wired into VS_CLASS_MAP and input tree |
| `dervet/MicrogridScenario.py` | Modified — CP imported and added to VS_CLASS_MAP |
| `Model_Parameters_Template_DER.json` | Modified — default CP parameter block added |
| `Results/scenario_comparison/SIMULATION_SUMMARY.md` | New file (documentation) |
| `Results/scenario_comparison/run_sizing_sweep.py` | New file (utility script) |

### Logic Changes

#### `storagevet/storagevet/ValueStreams/CoincidentPeakShaving.py` (new)

New `ValueStream` subclass implementing Coincident Peak shaving:

- **Constructor:** Reads `capacity_rate_monthly`, `transmission_rate_monthly`, `growth`, `pjm_5cp_dates`, `utility_1cp_dates` from params. Builds binary `pd.Series` indicators (`fivecp_indicator`, `onecp_indicator`) aligned to the full timeseries index.
- **`_build_indicator()`** — Maps `(date, hour_ending)` pairs to all sub-hourly timesteps within that clock hour.
- **`grow_drop_data()`** — Pads indicator series with zeros for years without CP data, then trims to only simulation years.
- **`objective_function()`** — Adds linear cost terms to the CVXPY objective for net load at CP timesteps:
  - 5CP weight: `capacity_rate * 12 / num_5cp_events` per timestep
  - 1CP weight: `transmission_rate * 12` per timestep
  - Both use `cvx.multiply(weight_param, net_load)` — **LP-compatible** (no new binary variables introduced).
- **`timeseries_report()`** — Outputs 5CP and 1CP indicator columns.
- **`drill_down_reports()`** — Produces `cp_event_detail` CSV with original vs. optimized load at each CP hour.
- **`proforma_report()`** — Extends base proforma with `Avoided CP Capacity Charges` and `Avoided CP Transmission Charges` columns, grown by the `growth` rate.

#### `storagevet/storagevet/ValueStreams/cp_registry.py` (new)

Hardcoded lookup table of historical CP event dates:
- **`CP_REGISTRY`**: nested dict keyed by year → `{pjm: set[CP], utilities: {UtilityEnum: set[CP]}}` with data for 2024 and 2025.
- **`parse_cp_dates_string()`**: Parses the `YYYY-MM-DD:HE` comma-separated string format used in model parameters into `(date, int)` tuples.

#### `storagevet/storagevet/Params.py`

- Added `self.CP = self.read_and_validate('CP')` in the service-reading block.
- In `check_...` method: if `CP` is not `None`, injects `dt` and `ts_index` into the params dict (required by the value stream's `_build_indicator`).

#### `storagevet/storagevet/Scenario.py` and `dervet/MicrogridScenario.py`

- Imported `CoincidentPeakShaving`.
- Added `'CP': CoincidentPeakShaving` to `VS_CLASS_MAP`.
- Added `'CP': input_tree.CP` to the input dict passed to value streams (Scenario only).

#### Schema files (`schema.json` / `Schema.json`)

Both the storagevet and dervet schemas were updated identically with a `CP` service block:
- Parameters: `capacity_rate_monthly` (float, $/kW-mo), `transmission_rate_monthly` (float, $/kW-mo), `pjm_5cp_dates` (string), `utility_1cp_dates` (string), `growth` (float, %/year).
- `max_num: "1"` — only one CP service instance allowed.

### Potential Concerns
- CP date data in `cp_registry.py` is hardcoded through 2025. Any simulation year beyond 2025 will receive zero CP indicators (no error raised). This is handled gracefully by `grow_drop_data()` but could silently produce incorrect results if a user expects CP shaving in future years.
- The `parse_cp_dates_string` function does not validate that dates fall within the simulation year — mismatched dates will produce zero-indicator rows with no warning.
- Net load formulation in `objective_function` includes `(-1) * generator_out_sum` and `(-1) * tot_variable_gen`, which is consistent with other value stream implementations.

---

## Commit 2 — `7f050ec` · Add Facility XX70 as example

### Files Changed
All new files under `Results/facility_70/`:
- `inputs/`: `model_parameters.json`, `timeseries.csv`, `tariff.csv`, `monthly.csv`, `yearly.csv`, `load_shed_percentage.csv`, one cycle life CSV.
- `results/`: Full set of result CSVs and log file from a completed run.

### Notes
- This commit adds a **reference example run** for a real or synthetic facility ("Facility 70") using the new CP value stream.
- No source code was changed.
- The `Results/` directory is listed in `.gitignore` (added in commit 4), but this subdirectory was committed explicitly. **Verify whether committing results is intentional policy** — these files are large (timeseries_results.csv is ~35k rows) and could cause repo bloat over time.

---

## Commit 1 — `1b64ffa` · Update facility 70 results and model parameters

### Files Changed
| File | Change Type |
|------|-------------|
| `storagevet/storagevet/Finances.py` | Modified — proforma net value calculation |
| `storagevet/storagevet/ValueStreams/DAEnergyTimeShift.py` | Modified — proforma report expanded |
| `dervet/CBA.py` | Modified — proforma and tax net value calculation |
| `requirements.txt` | Modified — `matplotlib` added |
| `requirements-conda.txt` | Modified — `matplotlib` added |
| `CLAUDE.md` | New file — project instructions for Claude Code |
| `Results/facility_70/` | Updated — all result CSVs, log, model parameters regenerated |
| `Results/scenario_comparison/` | Updated — sweep script, analysis MD, plots |

### Logic Changes

#### `storagevet/storagevet/Finances.py`

- Added class-level set `INFORMATIONAL_COLUMNS = {'DA ETS', 'DA Baseline Energy Cost', 'Baseline Energy Cost', 'Baseline Demand Cost'}`.
- Added class method `_value_columns(pro_forma)` — returns all column names except those in `INFORMATIONAL_COLUMNS` and `'Yearly Net Value'`.
- **Modified `proforma_report()`:** Changed `pro_forma['Yearly Net Value'] = pro_forma.sum(axis=1)` to `pro_forma.sum(axis=1)` → `pro_forma[self._value_columns(pro_forma)].sum(axis=1)`.
  - **Impact:** Informational/baseline columns no longer pollute the net value calculation. Previously, adding `DA Baseline Energy Cost` to the proforma would cause it to be double-counted in NPV.
- **Modified `calculate_yearly_avoided_cost()`:** Now also writes a `Baseline {charge_type} Cost` column (the raw original cost as a negative number) to `avoided_cost_df`. This is an informational column only; it does not affect optimization.

#### `storagevet/storagevet/ValueStreams/DAEnergyTimeShift.py`

- **Modified `proforma_report()`:** Previously wrote only `DA ETS` (total energy cost with battery). Now writes three columns per year:
  - `DA ETS` — total site energy cost at DA prices (with battery dispatch)
  - `DA Baseline Energy Cost` — what the site would pay without the battery (uses `Total Original Load (kW)` if available, falls back to `Total Load (kW)`)
  - `DA Arbitrage Value` — incremental savings = `DA ETS - DA Baseline Energy Cost`
- **Impact:** `DA Arbitrage Value` is the only column that should count toward `Yearly Net Value`. `DA ETS` and `DA Baseline Energy Cost` are now informational and excluded via `INFORMATIONAL_COLUMNS`. **This is a correctness fix** — previously `DA ETS` was the full energy cost (a large negative number), and including it in the proforma sum would have understated or zeroed out the project NPV.

#### `dervet/CBA.py`

- **Modified `proforma_report()`** (override): Changed `.sum(axis=1)` to `.sum(axis=1)` over `Financial._value_columns(proforma)` — consistent with base class fix.
- **Modified tax calculation block:** Added explicit filtering with `Financial.INFORMATIONAL_COLUMNS` before computing `yearly_net` for tax purposes. Prevents informational baseline columns from being taxed as income/loss.

### Potential Concerns
- The `DA Baseline Energy Cost` computation uses `results.get('Total Original Load (kW)', results.get('Total Load (kW)'))`. If neither column is present in results, this will silently return `None` and `baseline_cost` will be a scalar multiply of `None`, raising a runtime error. A guard should be added.
- `matplotlib` was added as a dependency but is only used in `run_sizing_sweep.py` (a utility script in `Results/`), not in the core model. Consider whether it belongs in `requirements.txt` or should be a dev/optional dependency.

---

## Cross-Cutting Observations

### Features Added
1. **LP-first optimization** — reduces solve time by avoiding MIP when the LP solution is clean.
2. **Coincident Peak (CP) value stream** — models PJM 5CP and utility 1CP charges with full-foresight shaving.
3. **Proforma correctness fix** — baseline energy cost columns are now excluded from NPV calculations.
4. **Solver safeguards** — GLPK_MI now has a 5-minute cap and 1% MIP gap tolerance.

### Features Revised
- `DAEnergyTimeShift.proforma_report()` — changed from single-column to three-column output; old `DA ETS` semantics preserved, arbitrage value now isolated in `DA Arbitrage Value`.
- `optimize_problem_loop()` in both `Scenario` and `MicrogridScenario` — refactored to delegate to `_solve_with_lp_first()`.

### Features Disabled
- None. No previously active features were disabled.

### Code Removed
- Several commented-out `print()` / `DEBUG` blocks in `MicrogridScenario.optimize_problem_loop()` were deleted (cleanup).
- One commented-out `self.system_requirements = {}` reset line was removed.

### Dependencies
- `matplotlib` added to both `requirements.txt` and `requirements-conda.txt`.
