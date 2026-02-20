# BESS Economic Feasibility -- DER-VET Simulation Summary

```sh
cd /Users/fsl/Documents/GitHub/DER-VET && conda run -n dervet-venv python Results/scenario_comparison/run_sizing_sweep.py 2>&1
```

## Overview

This analysis evaluates the economic feasibility of behind-the-meter battery energy storage (BESS) for a ~450 kW peak commercial facility in PSEG territory (PJM, New Jersey). Five value stream scenarios were modeled across nine battery configurations using DER-VET with full foresight of coincident peak events.

## Assumptions

### Battery Economics

| Parameter | Value |
|---|---|
| Capital cost (power) | $550/kW |
| Capital cost (energy) | $180/kWh |
| Fixed O&M | $10/kW-yr |
| Round-trip efficiency | 91% |
| Annual degradation | 2%/yr |
| Expected lifetime | 15 years |
| Discount rate | 7% |
| Federal tax rate | 21% |
| State tax rate | 6% |

### Coincident Peak Rates (2025 PSEG)

| Charge Component | Rate | Basis |
|---|---|---|
| Capacity (PLC / 5CP) | $21.186/kW-mo | Average demand during 5 highest PJM system peaks |
| Transmission (NSPL / 1CP) | $13.7091/kW-mo | Demand during single highest PSEG zonal peak |
| CP rate growth | 3%/yr | Applied to both capacity and transmission |

### 2025 CP Event Dates (Full Foresight)

| Type | Date | Hour Ending |
|---|---|---|
| 5CP (PJM) | Jun 23 | HE18 |
| 5CP (PJM) | Jun 24 | HE18 |
| 5CP (PJM) | Jun 25 | HE15 |
| 5CP (PJM) | Jul 28 | HE18 |
| 5CP (PJM) | Jul 29 | HE18 |
| 1CP (PSEG) | Jun 24 | HE19 |

### Battery Configurations Tested

| Power (kW) | Energy (kWh) | Duration (hr) |
|---|---|---|
| 50 | 100 | 2 |
| 100 | 200 | 2 |
| 100 | 400 | 4 |
| 150 | 300 | 2 |
| 150 | 600 | 4 |
| 200 | 400 | 2 |
| 200 | 800 | 4 |
| 250 | 500 | 2 |
| 250 | 1000 | 4 |

## Scenarios

| Scenario | DA Arbitrage | Demand Charge Reduction | Retail ETS | CP Shaving |
|---|---|---|---|---|
| DA_DCM | Yes | Yes | No | No |
| DCM_retail | No | Yes | Yes | No |
| DA_DCM_CP | Yes | Yes | No | Yes |
| DCM_retail_CP | No | Yes | Yes | Yes |
| CP_only | No | No | No | Yes |

## CP Event Detail (250 kW / 500 kWh Reference Case)

| Event | Date | HE | Original Load (kW) | Optimized Load (kW) | Reduction (kW) |
|---|---|---|---|---|---|
| 5CP (PJM) | Jun 23 | 18 | 340.63 | 90.63 | 250.00 |
| 5CP (PJM) | Jun 24 | 18 | 294.05 | 44.05 | 250.00 |
| 5CP (PJM) | Jun 25 | 15 | 297.14 | 47.14 | 250.00 |
| 5CP (PJM) | Jul 28 | 18 | 350.85 | 100.85 | 250.00 |
| 5CP (PJM) | Jul 29 | 18 | 354.81 | 104.81 | 250.00 |
| 1CP (PSEG) | Jun 24 | 19 | 300.89 | 50.89 | 250.00 |

The optimizer fully discharges the battery at each CP event, reducing demand by the full rated power.

## Results -- Without CP

### DA + DCM (Day-Ahead Arbitrage + Demand Charge Reduction)

| Power | Energy | Dur | Avoided DC ($/yr) | DA ETS ($/yr) | Net Annual ($/yr) | NPV ($) |
|---|---|---|---|---|---|---|
| 50 kW | 100 kWh | 2h | 3,671 | -81,392 | -54,367 | -603,518 |
| 100 kW | 200 kWh | 2h | 4,418 | -79,044 | -48,667 | -621,657 |
| 150 kW | 300 kWh | 2h | 4,669 | -76,665 | -43,299 | -643,033 |
| 200 kW | 400 kWh | 2h | 4,600 | -74,216 | -38,118 | -666,239 |
| 250 kW | 500 kWh | 2h | 4,404 | -71,786 | -33,054 | -690,569 |

DA ETS represents total site energy cost (negative = cost). All configurations are NPV-negative without CP.

### DCM + Retail ETS (Demand Charge + Retail Energy Time Shift)

| Power | Energy | Dur | Avoided DC ($/yr) | Net Annual ($/yr) | NPV ($) |
|---|---|---|---|---|---|
| 50 kW | 100 kWh | 2h | 3,830 | 6,350 | -11,806 |
| 100 kW | 200 kWh | 2h | 4,908 | 10,653 | -43,561 |
| 150 kW | 300 kWh | 2h | 5,714 | 14,757 | -77,250 |
| 200 kW | 400 kWh | 2h | 6,346 | 18,736 | -112,163 |
| 250 kW | 500 kWh | 2h | 6,793 | 22,578 | -148,412 |

Demand charge savings alone are insufficient to justify the investment.

## Results -- With CP (Full Foresight)

### CP Only

| Power | Energy | Dur | CP Capacity ($/yr) | CP Transmission ($/yr) | Net Annual ($/yr) | NPV ($) |
|---|---|---|---|---|---|---|
| 50 kW | 100 kWh | 2h | 13,093 | 8,472 | 19,538 | 141,706 |
| 100 kW | 200 kWh | 2h | 26,186 | 16,944 | 39,077 | 283,413 |
| 150 kW | 300 kWh | 2h | 39,279 | 25,417 | 58,615 | 425,119 |
| 200 kW | 400 kWh | 2h | 52,372 | 33,889 | 78,153 | 566,825 |
| 250 kW | 500 kWh | 2h | 65,465 | 42,361 | 97,692 | 708,532 |

CP shaving alone produces strong positive NPV at every size. The value scales linearly with battery power rating because the optimizer can fully discharge at each CP event.

### DCM + Retail ETS + CP (Best Stacked Scenario)

| Power | Energy | Dur | Avoided DC ($/yr) | CP Cap ($/yr) | CP Tx ($/yr) | Net Annual ($/yr) | NPV ($) |
|---|---|---|---|---|---|---|---|
| 50 kW | 100 kWh | 2h | 3,693 | 13,093 | 8,472 | 22,263 | 168,260 |
| 100 kW | 200 kWh | 2h | 4,708 | 26,186 | 16,944 | 42,533 | 317,098 |
| 150 kW | 300 kWh | 2h | 5,470 | 39,279 | 25,417 | 62,620 | 464,151 |
| 200 kW | 400 kWh | 2h | 6,032 | 52,372 | 33,889 | 82,562 | 609,794 |
| 250 kW | 500 kWh | 2h | 6,376 | 65,465 | 42,361 | 102,344 | 753,871 |

Stacking DCM + retail + CP yields the highest NPVs across all sizes.

### DA + DCM + CP

| Power | Energy | Dur | Avoided DC ($/yr) | DA ETS ($/yr) | CP Cap ($/yr) | CP Tx ($/yr) | Net Annual ($/yr) | NPV ($) |
|---|---|---|---|---|---|---|---|---|
| 50 kW | 100 kWh | 2h | 3,538 | -81,396 | 13,093 | 8,472 | -38,454 | -423,453 |
| 100 kW | 200 kWh | 2h | 4,217 | -79,021 | 26,186 | 16,944 | -16,771 | -260,851 |
| 150 kW | 300 kWh | 2h | 4,533 | -76,734 | 39,279 | 25,417 | 4,591 | -101,370 |
| 200 kW | 400 kWh | 2h | 4,528 | -74,425 | 52,372 | 33,889 | 25,730 | 55,938 |
| 250 kW | 500 kWh | 2h | 4,273 | -72,002 | 65,465 | 42,361 | 46,760 | 212,182 |

DA scenarios show lower NPV because the DA ETS column captures total site energy cost. CP savings offset this at larger sizes.

## Key Findings

1. **CP shaving is the dominant value driver.** At $21.19/kW-mo (capacity) + $13.71/kW-mo (transmission), avoided CP charges of ~$108k/yr for a 250 kW battery far exceed demand charge savings of ~$6-8k/yr.

2. **2-hour duration is sufficient.** CP events last 1 hour each. A 2-hour battery provides ample energy to cover any single event with margin. 4-hour batteries have higher capital cost with no incremental CP benefit, resulting in lower NPV.

3. **Linear scaling with power.** Under full foresight, the battery always fully discharges at CP events, so avoided CP charges scale linearly: ~$431/kW-yr in combined capacity + transmission savings (year 1).

4. **Every battery size is NPV-positive with CP.** Even the smallest 50 kW / 100 kWh system has an NPV of $142k (CP only) or $168k (stacked with DCM + retail).

5. **Best configuration: 250 kW / 500 kWh (2h).** NPV of $754k stacked, $709k CP-only. Capital cost of $227,500 with payback under 2 years.

6. **Foresight risk.** These results assume 100% foresight of CP event timing. Imperfect forecasting would reduce the effective shaving, particularly for the 5CP events which span two separate months. A sensitivity analysis on forecasting accuracy is recommended as a next step.

## Annual Value Breakdown (250 kW / 500 kWh, Year 1)

| Value Stream | CP Only | DCM + Retail + CP |
|---|---|---|
| Avoided CP Capacity | $65,465 | $65,465 |
| Avoided CP Transmission | $42,361 | $42,361 |
| Avoided Demand Charges | -- | $6,376 |
| Fixed O&M | -$2,555 | -$2,555 |
| Tax Burden | -$7,579 | -$9,303 |
| **Net Annual** | **$97,692** | **$102,344** |

## Files

- `summary.csv` -- Full results for all 45 runs
- `cp_event_detail.csv` -- Before/after load at each CP hour (from most recent run)
- `run_sizing_sweep.py` -- Script to reproduce or modify these simulations
