"""
CoincidentPeakShaving.py

Coincident Peak (5CP/1CP) shaving value stream for PJM territory.
Adds linear penalty terms to the objective for facility demand at known
CP hours, with full foresight.

Extension of DER-VET by Brightfield Inc.
"""
from storagevet.ValueStreams.ValueStream import ValueStream
from storagevet.ValueStreams.cp_registry import parse_cp_dates_string
import cvxpy as cvx
import numpy as np
import pandas as pd
from storagevet.ErrorHandling import *


class CoincidentPeakShaving(ValueStream):
    """Coincident Peak shaving for PJM 5CP (capacity/PLC) and 1CP (transmission/NSPL).

    With full foresight of CP event dates, the optimizer minimizes facility
    demand at those timesteps by discharging the battery (and pre-charging).

    Both cost terms are linear in net_load, preserving LP compatibility.
    """

    def __init__(self, params):
        ValueStream.__init__(self, 'CP', params)

        self.capacity_rate = params['capacity_rate_monthly']
        self.transmission_rate = params['transmission_rate_monthly']
        self.growth = params['growth'] / 100

        fivecp_dates = parse_cp_dates_string(params['pjm_5cp_dates'])
        onecp_dates = parse_cp_dates_string(params['utility_1cp_dates'])

        self.fivecp_dates = fivecp_dates
        self.onecp_dates = onecp_dates
        self.num_5cp = len(fivecp_dates)

        ts_index = params['ts_index']
        self.fivecp_indicator = self._build_indicator(ts_index, fivecp_dates)
        self.onecp_indicator = self._build_indicator(ts_index, onecp_dates)

        n_5cp_ts = self.fivecp_indicator.sum()
        n_1cp_ts = self.onecp_indicator.sum()
        TellUser.info(f"CP value stream: {n_5cp_ts} 5CP timesteps, "
                      f"{n_1cp_ts} 1CP timesteps mapped from index")

    def _build_indicator(self, ts_index, cp_date_list):
        """Build a binary pd.Series (0/1) aligned to ts_index.

        Each (date, hour_ending) pair maps to all sub-hourly timesteps within
        that clock hour.  Hour-ending N covers the interval [N-1:00, N:00).
        """
        indicator = pd.Series(0.0, index=ts_index)
        for cp_date, he in cp_date_list:
            hb = he - 1  # hour-beginning
            mask = ((ts_index.date == cp_date)
                    & (ts_index.hour == hb))
            indicator.loc[mask] = 1.0
        return indicator

    def grow_drop_data(self, years, frequency, load_growth):
        data_year = self.fivecp_indicator.index.year.unique()
        no_data_year = {pd.Period(year) for year in years} - \
                       {pd.Period(year) for year in data_year}
        if len(no_data_year) > 0:
            for yr in sorted(no_data_year):
                source_year = max(data_year)
                first_day = f'1/1/{yr.year}'
                last_day = f'1/1/{yr.year + 1}'
                new_index = pd.date_range(start=first_day, end=last_day,
                                          freq=frequency, inclusive='left')
                new_5cp = pd.Series(0.0, index=new_index)
                new_1cp = pd.Series(0.0, index=new_index)
                self.fivecp_indicator = pd.concat(
                    [self.fivecp_indicator, new_5cp])
                self.onecp_indicator = pd.concat(
                    [self.onecp_indicator, new_1cp])
        keep_years = set(years)
        keep_mask = self.fivecp_indicator.index.year.isin(keep_years)
        self.fivecp_indicator = self.fivecp_indicator.loc[keep_mask]
        self.onecp_indicator = self.onecp_indicator.loc[keep_mask]

    def objective_function(self, mask, load_sum, tot_variable_gen,
                           generator_out_sum, net_ess_power,
                           annuity_scalar=1):
        net_load = (load_sum + net_ess_power
                    + (-1) * generator_out_sum
                    + (-1) * tot_variable_gen)

        sub_5cp = self.fivecp_indicator.loc[mask].values
        sub_1cp = self.onecp_indicator.loc[mask].values

        total_cp_cost = 0

        if np.any(sub_5cp > 0):
            coeff_5cp = self.capacity_rate * 12.0 * self.dt / self.num_5cp
            p_5cp = cvx.Parameter(value=sub_5cp * coeff_5cp,
                                  shape=sum(mask), name='CP_5cp_weight')
            total_cp_cost += cvx.sum(cvx.multiply(p_5cp, net_load)) \
                             * annuity_scalar

        if np.any(sub_1cp > 0):
            coeff_1cp = self.transmission_rate * 12.0 * self.dt
            p_1cp = cvx.Parameter(value=sub_1cp * coeff_1cp,
                                  shape=sum(mask), name='CP_1cp_weight')
            total_cp_cost += cvx.sum(cvx.multiply(p_1cp, net_load)) \
                             * annuity_scalar

        if isinstance(total_cp_cost, (int, float)) and total_cp_cost == 0:
            return {}

        return {self.name: total_cp_cost}

    def timeseries_report(self):
        report = pd.DataFrame(index=self.fivecp_indicator.index)
        report.loc[:, 'CP 5CP Indicator'] = self.fivecp_indicator
        report.loc[:, 'CP 1CP Indicator'] = self.onecp_indicator
        return report

    def drill_down_reports(self, **kwargs):
        time_series_data = kwargs.get('time_series_data')
        if time_series_data is None:
            return {}

        original_load_col = 'Total Original Load (kW)' \
            if 'Total Original Load (kW)' in time_series_data.columns \
            else 'Total Load (kW)'
        original_load = time_series_data[original_load_col]
        net_load = time_series_data['Net Load (kW)']

        rows = []
        for cp_date, he in self.fivecp_dates:
            hb = he - 1
            ts_mask = ((time_series_data.index.date == cp_date)
                       & (time_series_data.index.hour == hb))
            if ts_mask.any():
                orig_avg = original_load.loc[ts_mask].mean()
                opt_avg = net_load.loc[ts_mask].mean()
                rows.append({
                    'Type': '5CP (PJM)',
                    'Date': cp_date,
                    'Hour Ending': he,
                    'Original Load (kW)': round(orig_avg, 2),
                    'Optimized Load (kW)': round(opt_avg, 2),
                    'Reduction (kW)': round(orig_avg - opt_avg, 2),
                })

        for cp_date, he in self.onecp_dates:
            hb = he - 1
            ts_mask = ((time_series_data.index.date == cp_date)
                       & (time_series_data.index.hour == hb))
            if ts_mask.any():
                orig_avg = original_load.loc[ts_mask].mean()
                opt_avg = net_load.loc[ts_mask].mean()
                rows.append({
                    'Type': '1CP (Utility)',
                    'Date': cp_date,
                    'Hour Ending': he,
                    'Original Load (kW)': round(orig_avg, 2),
                    'Optimized Load (kW)': round(opt_avg, 2),
                    'Reduction (kW)': round(orig_avg - opt_avg, 2),
                })

        if not rows:
            return {}

        cp_detail = pd.DataFrame(rows)
        cp_detail.set_index(['Type', 'Date'], inplace=True)
        return {'cp_event_detail': cp_detail}

    def proforma_report(self, opt_years, apply_inflation_rate_func,
                        fill_forward_func, results):
        proforma = super().proforma_report(opt_years, apply_inflation_rate_func,
                                           fill_forward_func, results)

        original_load_col = 'Total Original Load (kW)' \
            if 'Total Original Load (kW)' in results.columns \
            else 'Total Load (kW)'
        original_load = results[original_load_col]
        net_load = results['Net Load (kW)']

        for year in opt_years:
            yr_5cp = self.fivecp_indicator[
                self.fivecp_indicator.index.year == year]
            yr_1cp = self.onecp_indicator[
                self.onecp_indicator.index.year == year]

            avoided_5cp = 0.0
            if yr_5cp.sum() > 0:
                mask_5cp = yr_5cp > 0
                orig_plc = (original_load.loc[mask_5cp.index[mask_5cp]]
                            .mean())
                new_plc = net_load.loc[mask_5cp.index[mask_5cp]].mean()
                avoided_5cp = ((orig_plc - new_plc)
                               * self.capacity_rate * 12.0)

            avoided_1cp = 0.0
            if yr_1cp.sum() > 0:
                mask_1cp = yr_1cp > 0
                orig_nspl = (original_load.loc[mask_1cp.index[mask_1cp]]
                             .mean())
                new_nspl = net_load.loc[mask_1cp.index[mask_1cp]].mean()
                avoided_1cp = ((orig_nspl - new_nspl)
                               * self.transmission_rate * 12.0)

            period = pd.Period(year=year, freq='Y')
            proforma.loc[period, 'Avoided CP Capacity Charges'] = avoided_5cp
            proforma.loc[period, 'Avoided CP Transmission Charges'] = \
                avoided_1cp

        proforma = fill_forward_func(proforma, self.growth)
        return proforma
