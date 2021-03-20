import os
import pandas as pd
import time
from datetime import datetime
import logging

from src.utils.constants import PATH_HIST_KLINES
from src.account.test_account import TestAccount
from src.utils.chart import Chart
from src.engine.engine import Engine
from src.engine.bybit_rest import BybitRest
from src.utils.utils import get_logger, interval_bybit_notation, date_to_seconds

logger = get_logger(logging.getLogger(__name__), 'logs/backtester.log', logging.DEBUG)

class Backtester(Engine):
    def __init__(self, *args, **kwargs):
        super().__init__(strategy =  kwargs.get('strategy'), symbol = kwargs.get('symbol'))

        api_key = kwargs.get('api_key')
        secret = kwargs.get('secret')
        
        self.bybit = BybitRest(api_key = api_key, secret = secret, symbol = self.symbol)

        self.start_ts = date_to_seconds(kwargs.get('args')[0])
        self.end_ts = date_to_seconds(kwargs.get('args')[1])

        #setup account
        self.account = TestAccount(startbalance = 1)

        #aggregate klines
        tic = time.perf_counter()
        kline_dict = self.aggregate_local_and_hist_klines('BTCUSD', ['1h', '15m', '1m'])

        # constructing working set
        self.klines['1m'] = kline_dict['1m'].loc[[x for x in range(self.start_ts, self.end_ts, 60)]]
        self.klines['15m'] = kline_dict['15m'].loc[[x for x in range(self.start_ts, self.end_ts, 900)]]
        self.klines['1h'] = kline_dict['1h'].loc[[x for x in range(self.start_ts, self.end_ts, 3600)]]

        toc = time.perf_counter()
        print(f"aggregate klines: {toc-tic:.4f}")

        tic = time.perf_counter()
        table = self._get_indis()
        toc = time.perf_counter()
        print(f"join indis: {toc-tic:.4f}")

        #go for it
        tic = time.perf_counter()
        self.execute_strategy(table)
        toc = time.perf_counter()
        print(f"execute: {toc-tic:.4f}")
        logger.info(self.account.getResult())
        print(self.account.getResult())

        chart = Chart(account = self.account, risk = self.risk)

    def process_kline(self, row, signals):
        try:
            if self._check_risk_management():
                if self._check_time(row):
                    signal = self._check_signal(row, signals)

                    if signal == "long":
                        atr = row['atr']
                        sl = round(row['Open'] - 1 * atr, 2)
                        tp = round(row['Open'] + 0.95 * atr, 2)
                        logger.info(f"{row['Date']}: LONG {row['Open']} SL {sl} TP {tp}")
                        logger.info(row)
                        self.account.open('long', row['Open'], sl, tp, self.risk, row.name)
                    if signal == "short":
                        atr = row['atr']
                        sl = round(row['Open'] + 1 * atr, 2)
                        tp = round(row['Open'] - 0.95 * atr, 2)
                        logger.info(f"{row['Date']}: SHORT {row['Open']} SL {sl} TP {tp}")
                        logger.info(row)
                        self.account.open('short', row['Open'], sl, tp, self.risk, row.name)

            # update account
            self.account.update(row.name, row)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"error at {row.name}: {e} ")

    def execute_strategy(self, table):
        table.apply(self.process_kline, axis = 1, signals = self.signals)


    def aggregate_local_and_hist_klines(self, symbol, intervals):
        """Aggregate local klines with bybit klines
        :param symbol: Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
        :type symbol: str
        :param intervals: array of Bybit Kline intervals -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
        :type intervals: []
        :return: dict of pandas Dataframes, containing OHLCV values
        """    
        result = {}

        for interval in intervals:
            filename = PATH_HIST_KLINES[interval]
            file_klines = pd.DataFrame()

            request_begin = strat_begin = self.start_ts - 300000
            write_mode = 'w'

            try:
                file_klines = pd.read_csv(filename, index_col=0, names = ["Open","High","Low","Close","Volume","TurnOver","Date"])
                file_klines.loc[:,'Date'] = [datetime.fromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in file_klines.index]
                newest = file_klines.tail(1).index[0]
                oldest = file_klines.head(1).index[0]
                if oldest - strat_begin > interval_bybit_notation(interval) * 60:
                    request_begin = strat_begin
                    write_mode = 'w'
                    file_klines = pd.DataFrame()
                else:
                    request_begin = int(newest) + interval_bybit_notation(interval) * 60
                    write_mode = 'a'
            except FileNotFoundError as err:
                pass

            bybit_klines = pd.DataFrame()
            if request_begin < int(datetime.now().timestamp()):
                output_data = self.bybit.get_hist_klines(symbol, interval_bybit_notation(interval), str(request_begin))
                column_data = [i[1:] for i in output_data]
                index = [int(i[0]) for i in output_data]
                # convert to data frame
                bybit_klines = pd.DataFrame(column_data, index = index, columns=['Open', 'High', 'Low', 'Close', 'Volume', 'TurnOver'])
                bybit_klines.loc[:,'Date'] = [datetime.fromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in bybit_klines.index]

                bybit_klines.to_csv(filename, header = False,  mode=write_mode)

            result[interval] = pd.concat([file_klines, bybit_klines]) if not len(bybit_klines.index) == 0 else file_klines

        return result
