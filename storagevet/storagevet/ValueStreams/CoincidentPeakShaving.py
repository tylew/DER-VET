"""
CoincidentPeakShaving.py

Coincident Peak shaving value stream for PJM territory.
Supports N discrete CP event types (e.g. PJM 5CP, JCPL 5CP, PSEG 1CP),
each as a separate instance with its own rate, dates, and label.

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
    """Coincident Peak shaving for a single CP event type.

    Each instance represents one set of CP events (e.g. "PJM 5CP" or
    "PSEG 1CP") with its own monthly rate and event dates.  Multiple
    instances can coexist in the ServiceAggregator, each contributing
    an independent objective term.

    With full foresight of CP event dates, the optimizer minimizes facility
    demand at those timesteps by discharging the battery (and pre-charging).
    The cost term is linear in net_load, preserving LP compatibility.
    """

    def __init__(self, params):
        instance_id = params.get('ID', '')
        name = f"CP-{instance_id}" if instance_id else 'CP'
        ValueStream.__init__(self, name, params)

        self.instance_id = instance_id
        self.label = params['label']
        self.rate = params['rate_monthly']
        self.growth = params['growth'] / 100

        self.cp_dates = parse_cp_dates_string(params['cp_dates'])
        self.num_events = len(self.cp_dates)

        ts_index = params['ts_index']
        self.indicator = self._build_indicator(ts_index, self.cp_dates)

        n_ts = int(self.indicator.sum())
        TellUser.info(f"CP value stream '{self.label}' ({self.name}): "
                      f"{self.num_events} events, {n_ts} timesteps matched")

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
        data_year = self.indicator.index.year.unique()
        no_data_year = {pd.Period(year) for year in years} - \
                       {pd.Period(year) for year in data_year}
        if len(no_data_year) > 0:
            for yr in sorted(no_data_year):
                first_day = f'1/1/{yr.year}'
                last_day = f'1/1/{yr.year + 1}'
                new_index = pd.date_range(start=first_day, end=last_day,
                                          freq=frequency, inclusive='left')
                new_ind = pd.Series(0.0, index=new_index)
                self.indicator = pd.concat([self.indicator, new_ind])
        keep_years = set(years)
        keep_mask = self.indicator.index.year.isin(keep_years)
        self.indicator = self.indicator.loc[keep_mask]

    def objective_function(self, mask, load_sum, tot_variable_gen,
                           generator_out_sum, net_ess_power,
                           annuity_scalar=1):
        net_load = (load_sum + net_ess_power
                    + (-1) * generator_out_sum
                    + (-1) * tot_variable_gen)

        sub_ind = self.indicator.loc[mask].values

        if not np.any(sub_ind > 0):
            return {}

        coeff = self.rate * 12.0 * self.dt / self.num_events
        p_weight = cvx.Parameter(value=sub_ind * coeff,
                                 shape=sum(mask),
                                 name=f'{self.name}_weight')
        cost = cvx.sum(cvx.multiply(p_weight, net_load)) * annuity_scalar

        return {self.name: cost}

    def timeseries_report(self):
        report = pd.DataFrame(index=self.indicator.index)
        report.loc[:, f'{self.name} Indicator'] = self.indicator
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
        for cp_date, he in self.cp_dates:
            hb = he - 1
            ts_mask = ((time_series_data.index.date == cp_date)
                       & (time_series_data.index.hour == hb))
            if ts_mask.any():
                orig_avg = original_load.loc[ts_mask].mean()
                opt_avg = net_load.loc[ts_mask].mean()
                rows.append({
                    'Type': self.label,
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
        report_key = f'cp_event_detail_{self.instance_id}' \
            if self.instance_id else 'cp_event_detail'
        return {report_key: cp_detail}

    def proforma_report(self, opt_years, apply_inflation_rate_func,
                        fill_forward_func, results):
        proforma = super().proforma_report(opt_years, apply_inflation_rate_func,
                                           fill_forward_func, results)

        original_load_col = 'Total Original Load (kW)' \
            if 'Total Original Load (kW)' in results.columns \
            else 'Total Load (kW)'
        original_load = results[original_load_col]
        net_load = results['Net Load (kW)']

        col_name = f'Avoided CP Charges ({self.label})'

        for year in opt_years:
            yr_ind = self.indicator[self.indicator.index.year == year]

            avoided = 0.0
            if yr_ind.sum() > 0:
                active_mask = yr_ind > 0
                orig_avg = original_load.loc[active_mask.index[active_mask]].mean()
                new_avg = net_load.loc[active_mask.index[active_mask]].mean()
                avoided = (orig_avg - new_avg) * self.rate * 12.0

            period = pd.Period(year=year, freq='Y')
            proforma.loc[period, col_name] = avoided

        proforma = fill_forward_func(proforma, self.growth)
        return proforma
