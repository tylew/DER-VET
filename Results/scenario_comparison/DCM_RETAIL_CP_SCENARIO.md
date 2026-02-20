# DA + DCM + CP Scenario -- Economic Analysis

**Configuration:** 250 kW / 500 kWh (2-hour duration) BESS
**Facility:** ~392 kW peak commercial load, PSEG territory (PJM, NJ)
**Scenario:** Day-Ahead Energy Arbitrage + Demand Charge Reduction + Coincident Peak Shaving
**Foresight:** 100% (CP event dates/times known in advance)

---

## System Economics

| Parameter | Value |
|---|---|
| Total Capital Cost | $227,500 ($550/kW + $180/kWh) |
| Fixed O&M | $2,500/yr ($10/kW-yr, escalating 2.2%/yr) |
| Round-trip Efficiency | 91% |
| Annual Degradation | 2%/yr |
| Project Lifetime | 15 years |
| Discount Rate | 7% |
| Tax Rate | 27% effective (21% federal + 6% state) |

---

## 15-Year Financial Summary

| Metric | Value |
|---|---|
| **NPV** | **$815,106** |
| **Simple Payback** | **Year 3** |
| Total Undiscounted Net Value | $1,408,389 |

### Baseline Facility Costs (informational, excluded from NPV)

| Baseline Cost | Annual | 15-Year Total |
|---|---|---|
| DA Baseline Energy Cost | -$84,129/yr | -$1,261,930 |
| Baseline Tariff Energy Cost | -$59,371/yr | -$890,564 |
| Baseline Tariff Demand Cost | -$35,066/yr | -$525,990 |

These represent what the facility pays regardless of the battery. They are tracked in the pro forma for transparency but excluded from the NPV and Yearly Net Value calculations.

---

## Year 1 Revenue Breakdown

| Line Item | Annual Value | Type |
|---|---|---|
| Avoided CP Capacity Charges (5CP) | $63,558 | Value |
| Avoided CP Transmission Charges (1CP) | $41,127 | Value |
| DA Arbitrage Value | $10,959 | Value |
| Avoided Demand Charges (DCM) | $4,548 | Value |
| Avoided Energy Charge | -$781 | Value |
| Fixed O&M | -$2,500 | Cost |
| Federal Tax Burden | -$23,078 | Cost |
| State Tax Burden | -$7,015 | Cost |
| Capital Cost | -$227,500 | Cost |
| **Year 1 Net** | **-$140,681** | |
| | | |
| DA ETS (site energy cost w/ battery) | -$73,169 | Info |
| DA Baseline Energy Cost (w/o battery) | -$84,129 | Info |
| Baseline Tariff Energy Cost | -$59,371 | Info |
| Baseline Tariff Demand Cost | -$35,066 | Info |

Year 1 is net-negative due to upfront capital. By Year 2, net annual value reaches **$108,627**.

### Pro Forma Methodology

The pro forma now separates **value columns** (included in NPV) from **informational columns** (tracked but excluded):

- **DA Arbitrage Value** (+$10,959): the incremental energy savings from battery dispatch. This is `DA Baseline Energy Cost - DA ETS` = the difference between what the site would pay without the battery vs. with it. Included in NPV.
- **DA ETS** (-$73,169): total site energy cost at DA prices with the battery operating. Informational only.
- **DA Baseline Energy Cost** (-$84,129): total site energy cost at DA prices without the battery. Informational only.
- **Baseline Tariff Energy/Demand Costs**: what the site pays under its retail tariff regardless of the battery. Informational only.

---

## Value Stream #1: Coincident Peak Capacity Charges (5CP)

**Rate:** $21.186/kW-month | **Growth:** 3%/yr | **15-year total:** $1,182,110

| 5CP Event | Date | Hour Ending | Original Load | Optimized Load | Reduction |
|---|---|---|---|---|---|
| 1 | Jun 23 | HE18 | 340.6 kW | 90.6 kW | 250.0 kW |
| 2 | Jun 24 | HE18 | 294.1 kW | 44.1 kW | 250.0 kW |
| 3 | Jun 25 | HE15 | 297.1 kW | 47.1 kW | 250.0 kW |
| 4 | Jul 28 | HE18 | 350.9 kW | 100.9 kW | 250.0 kW |
| 5 | Jul 29 | HE18 | 354.8 kW | 104.8 kW | 250.0 kW |

**PLC reduction:** 327.5 kW avg to 77.5 kW avg = **250.0 kW shaved**

Annual savings: 250.0 kW x $21.186/kW-mo x 12 = **$63,558/yr**

---

## Value Stream #2: Coincident Peak Transmission Charges (1CP)

**Rate:** $13.7091/kW-month | **Growth:** 3%/yr | **15-year total:** $764,923

| 1CP Event | Date | Hour Ending | Original Load | Optimized Load | Reduction |
|---|---|---|---|---|---|
| 1 | Jun 24 | HE19 | 300.9 kW | 50.9 kW | 250.0 kW |

**NSPL reduction:** 300.9 kW to 50.9 kW = **250.0 kW shaved**

Annual savings: 250.0 kW x $13.7091/kW-mo x 12 = **$41,127/yr**

---

## Value Stream #3: Day-Ahead Energy Arbitrage

**Year 1:** $10,959 | **15-year total:** $164,388

The battery charges during low-price hours and discharges during high-price hours. DA prices range from -$51/MWh to $1,986/MWh (mean $42.60/MWh).

### Monthly Arbitrage Breakdown

| Month | Baseline Cost | Cost w/ Battery | Arbitrage Savings | Max Discharge | Max Charge |
|---|---|---|---|---|---|
| Jan | $7,905 | $6,784 | $1,121 | 199 kW | -103 kW |
| Feb | $5,921 | $5,235 | $686 | 204 kW | -80 kW |
| Mar | $4,939 | $4,295 | $644 | 214 kW | -80 kW |
| Apr | $5,360 | $4,737 | $624 | 250 kW | -85 kW |
| May | $4,963 | $4,391 | $573 | 250 kW | -97 kW |
| Jun | $10,578 | $8,457 | **$2,121** | 250 kW | -186 kW |
| Jul | $11,820 | $10,572 | $1,248 | 250 kW | -158 kW |
| Aug | $7,040 | $6,325 | $714 | 250 kW | -152 kW |
| Sep | $5,405 | $4,929 | $475 | 250 kW | -113 kW |
| Oct | $5,836 | $4,854 | $982 | 250 kW | -104 kW |
| Nov | $5,799 | $5,242 | $556 | 241 kW | -82 kW |
| Dec | $8,562 | $7,348 | **$1,214** | 217 kW | -114 kW |
| **Total** | **$84,129** | **$73,169** | **$10,959** | | |

June is the best arbitrage month ($2,121), driven by high price volatility during summer peaks.

---

## Value Stream #4: Demand Charge Reduction (DCM)

**Year 1:** $4,548 | **15-year total:** $68,223

### Monthly Peak Impacts

| Month | Original Peak | Net Peak | Reduction | Notes |
|---|---|---|---|---|
| Jan | 207.1 kW | 255.7 kW | **-48.7 kW** | Peak increased by charging |
| Feb | 212.5 kW | 227.6 kW | **-15.0 kW** | Peak increased by charging |
| Mar | 224.4 kW | 228.3 kW | **-4.0 kW** | Peak increased by charging |
| Apr | 279.5 kW | 255.5 kW | 24.0 kW | |
| May | 326.9 kW | 275.4 kW | 51.5 kW | |
| Jun | 374.4 kW | 366.1 kW | 8.3 kW | CP priority limits DCM |
| Jul | 392.0 kW | 378.7 kW | 13.2 kW | CP priority limits DCM |
| Aug | 387.6 kW | 361.8 kW | 25.8 kW | |
| Sep | 343.0 kW | 335.8 kW | 7.2 kW | |
| Oct | 289.2 kW | 269.6 kW | 19.6 kW | |
| Nov | 290.6 kW | 251.5 kW | 39.1 kW | |
| Dec | 217.7 kW | 271.4 kW | **-53.6 kW** | Peak increased by charging |

In Jan, Feb, Mar, and Dec, the optimizer increases monthly peaks by charging during high-price hours that coincide with peak periods. This is the correct economic tradeoff -- the energy arbitrage revenue exceeds the demand charge penalty in every case.

---

## Battery Utilization

| Metric | Value |
|---|---|
| Avg daily cycles | 1.44 |
| Annual discharge energy | 263,255 kWh |
| Annual charge energy | 289,291 kWh |
| Max discharge | 250 kW |
| Max charge | -186 kW |

---

## Revenue Growth Over Project Life

| Year | CP Capacity | CP Transmission | DCM (w/ DA) | DCM (w/o DA) | DA Arb | Total w/ DA | Total w/o DA |
|---|---|---|---|---|---|---|---|
| 1 (2025) | $63,558 | $41,127 | $4,548 | $6,376 | $10,959 | $120,192 | $111,061 |
| 2 (2026) | $65,465 | $42,361 | $4,548 | $6,376 | $10,959 | $123,333 | $114,202 |
| 5 (2029) | $71,535 | $46,289 | $4,548 | $6,376 | $10,959 | $133,331 | $124,200 |
| 10 (2034) | $82,929 | $53,662 | $4,548 | $6,376 | $10,959 | $152,098 | $142,967 |
| 15 (2039) | $96,137 | $62,209 | $4,548 | $6,376 | $10,959 | $173,853 | $164,722 |

DCM is lower with DA active ($4,548 vs $6,376) because the optimizer sometimes increases monthly peaks to capture higher-value energy arbitrage. The net DA advantage is $9,131/yr ($10,959 arb - $1,828 DCM reduction).

---

## Scenario Comparison

| Metric | DA + DCM + CP | Retail + DCM + CP |
|---|---|---|
| **NPV (15yr)** | **$815,106** | **$753,871** |
| Simple Payback | Year 3 | Year 3 |
| Year 2 Net | $108,627 | $102,344 |
| CP Savings (yr 1) | $104,685 | $104,685 |
| DCM Savings (yr 1) | $4,548 | $6,376 |
| DA Arbitrage (yr 1) | $10,959 | n/a |
| Energy Charge Impact (yr 1) | -$781 | -$111 |
| Battery gross value (yr 1) | $119,411 | $110,950 |
| Daily cycles | 1.44 | 0.21 |

With the corrected pro forma (baseline energy costs excluded from NPV in both scenarios), the DA scenario shows a **$61,235 higher NPV** due to the $10,959/yr in real arbitrage value from hourly price spreads.

The DA scenario has slightly lower demand charge savings ($4,548 vs $6,376) because the optimizer sometimes increases peak load to capture energy arbitrage. The $1,828/yr DCM reduction is more than offset by the $10,959/yr arbitrage gain.

---

## Key Takeaways

1. **CP shaving remains the dominant value at ~$105k/yr** (88% of Year 1 gross revenue), regardless of energy pricing model.

2. **DA arbitrage adds $10,959/yr** (9.2% of gross revenue) by exploiting hourly price spreads. This is a real incremental gain over flat retail pricing.

3. **The corrected pro forma enables direct comparison.** By excluding baseline facility energy costs from the NPV calculation, both DA and retail scenarios are evaluated on the battery's incremental economics. The DA scenario is worth $61k more in NPV.

4. **Arbitrage conflicts with demand charge reduction** in winter months, but the optimizer correctly prioritizes the higher-value energy trades.

5. **Battery cycles 7x more with DA active** (1.44 vs 0.21 cycles/day). This improves revenue but accelerates degradation -- cycle-based degradation modeling is recommended.

6. **Foresight risk remains the critical factor.** These results assume 100% foresight of CP event timing.

---

## Source Files

- `Results/facility_70/results/pro_forma.csv` -- 15-year pro forma with value + informational columns
- `Results/facility_70/results/timeseries_results.csv` -- 15-minute dispatch results
- `Results/facility_70/results/cp_event_detail.csv` -- Before/after load at each CP hour
- `Results/scenario_comparison/plots/` -- Visualizations
  - `full_year_load_vs_battery.png` -- Annual load and battery dispatch
  - `cp_event_*.png` -- 48-hour windows around each CP event
  - `arbitrage_day_20251214.png` -- Best non-CP arbitrage day (Dec 14)

## Pro Forma Modifications

The DER-VET pro forma was modified to improve cross-scenario comparability:

1. **`DAEnergyTimeShift.proforma_report`**: Now reports three columns instead of one:
   - `DA ETS` (informational): total site energy cost with battery
   - `DA Baseline Energy Cost` (informational): total site energy cost without battery
   - `DA Arbitrage Value` (value): incremental savings from battery dispatch

2. **`Finances.calculate_yearly_avoided_cost`**: Now also reports:
   - `Baseline Energy Cost` (informational): annual tariff energy bill without battery
   - `Baseline Demand Cost` (informational): annual tariff demand bill without battery

3. **`Finances.proforma_report` and `CBA.proforma_report`**: `Yearly Net Value` now excludes informational columns so that NPV reflects only the battery's incremental economics.
