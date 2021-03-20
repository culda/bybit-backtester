import pandas as pd
import numpy as np
from datetime import datetime

from src.utils.indicators import calc_indi
from src.utils.utils import get_logger, start_of_min15, start_of_hour, start_of_hour4, start_of_day, date_to_seconds, interval_bybit_notation

class Engine():

    def __init__(self, **kwargs):
        self.strategy = kwargs.get('strategy')
        self.symbol = kwargs.get("symbol")
        self.klines = {
            '1h': pd.DataFrame(),
            '15m': pd.DataFrame(),
            '1m': pd.DataFrame()
        }
        self.signals = [s.get('name') for s in self.strategy.get('signal')]
        self.risk = self.strategy.get('risk')

    def _check_signal(self, row, signals):
        if all([row[s] for s in signals]) and row['Open'] > row['daily_open']:
            return "long"

        go_short = True
        for s in signals:
            if row[s] == None or row[s] == True:
                go_short = False
        if go_short and row['Open'] < row['daily_open']:
            return "short"

    def _check_time(self, row):
        no_trade_hours = self.strategy.get('no-trade-hours')
        hour = datetime.fromtimestamp(row.name).hour
        return not hour in no_trade_hours

    def _check_risk_management(self):
        return self.account.dailywon < 1 and self.account.dailylost <= 3 and self.account.trade == None

    def _get_indis(self):
        indis = self._calc_indis(self.strategy.get('signal'), self.strategy.get('atr'))
        return self._join_indis(indis)

    def _calc_indis(self, signal, atr):
        frames = {}
        indis = [s for s in signal] + [atr]
        for indi in indis:
            interval, result = calc_indi(indi, self.klines)
            frames[interval] = pd.DataFrame(result) if not interval in frames else pd.concat([frames[interval], result], axis = 1)

        return frames

    def _join_indis(self, indis):
        # join indis to 1m klines
        def htf_1h_ts(row):
            return row.name - datetime.fromtimestamp(row.name).minute * 60

        def htf_15m_ts(row):
            return row.name - (datetime.fromtimestamp(row.name).minute - datetime.fromtimestamp(row.name).minute // 15 * 15) * 60

        timestamp_mapping_dict = {
            '15m': htf_15m_ts,
            '1h': htf_1h_ts
        }
        result = self.klines['1m']
        #add daily open
        result['daily_open'] = result.apply(lambda row: row['Open'] if start_of_day(row.name) else np.nan , axis = 1).fillna(method="ffill")

        for interval in indis:
            result[interval] = result.apply(timestamp_mapping_dict[interval], axis = 1)
            result = result.join(indis[interval], on=interval)

        return result