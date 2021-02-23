import logging
import pandas as pd
import pandas_ta as ta
from datetime import datetime

from utils import get_logger, start_of_hour, start_of_day, date_to_seconds
from ems_bybit import Bybit
from constants import BYBIT_PUBLIC_TRADE, BYBIT_SECRET_TRADE
from tick_service import aggregate_local_and_hist_klines
from indicators import hma
from backtester import Backtester

logger = get_logger(logging.getLogger(__name__), 'logs/skalpit.log', logging.DEBUG)

class Skalpit():
    def __init__(self, *args, **kwargs):
        self.bybit = Bybit(BYBIT_PUBLIC_TRADE, BYBIT_SECRET_TRADE, 'BTCUSD', True)
        self.klines = {
            '1h': pd.DataFrame(),
            '1m': pd.DataFrame()
        }
        
        self.klines = aggregate_local_and_hist_klines(self.bybit, 'BTCUSD', ['1m', '1h'])

        self.hull1h = pd.DataFrame({'hull0' : ta.hma(self.klines['1h']['Close'], 55) , 'hull2': ta.hma(self.klines['1h']['Close'], 55, 2)})
        self.hull1h['overlap'] = self.hull1h.apply(lambda row: row['hull0'] > row['hull2'], axis = 1)

        self.atr1h = pd.DataFrame({'atr1h-24': ta.atr(self.klines['1h']['High'], self.klines['1h']['Low'], self.klines['1h']['Close'], 24)})

        self.tester = Backtester()
        self.risk = 5

        self.execute_strategy("2021-02-20 00:00:00", "2021-02-23 10:00:00")

        logger.info(self.tester.getResult())

        print(self.tester.getResult())


    def execute_strategy(self, start, end):
        """
        start should be any day at 00:00:00 
        """
        start_ts = date_to_seconds(start)
        end_ts = date_to_seconds(end)
        daily_open = self.klines['1m'].loc[start_ts]['Open']
        hour_ts = start_ts        

        index = start_ts
        while index < end_ts:
            try:
                row = self.klines['1m'].loc[index]
                if start_of_hour(index):
                    hour_ts = index
                if start_of_day(index):
                    daily_open = row["Open"]

                if self._check_risk_management():
                    #SL at hourly low or atr24, whichever is lowest
                    #TP at 0.95 * atr24
                    signal = self._check_signal(index, row['Open'], hour_ts, daily_open)
                    if signal == "long":
                        atr24 = self.atr1h.loc[hour_ts]['atr1h-24']
                        sl = round(row['Open'] - min(atr24, self.klines['1h'].loc[hour_ts]['Low']), 2)
                        tp = round(row['Open'] + 0.95 * atr24, 2)
                        logger.info(f"{row['Date']}: LONG {row['Open']} SL {sl} TP {tp}")
                        self.tester.open('long', row['Open'], sl, tp, self.risk, index)
                    if signal == "short":
                        atr24 = round(self.atr1h.loc[hour_ts]['atr1h-24'], 2)
                        sl = round(row['Open'] + min(atr24, self.klines['1h'].loc[hour_ts]['Low']), 2)
                        tp = round(row['Open'] - 0.95 * atr24, 2)
                        logger.info(f"{row['Date']}: SHORT {row['Open']} SL {sl} TP {tp}")
                        self.tester.open('short', row['Open'], sl, tp, self.risk, index)

                # update backtester
                self.tester.update(index, row)
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"error at {index}: {e} ")

            index += 60

    def _get_trade_details(self, ts):
        # entry price
        # SL + TP
        pass

    def _check_risk_management(self):
        return self.tester.dailywon <= 1 and self.tester.dailylost <= 3 and self.tester.trade == None
        # drawdown < 30%

    def _check_signal(self, ts, price, hour_ts, daily_open):
        #check for long
        if self.hull1h.loc[hour_ts]['overlap'] and price > daily_open:
            return "long"

        #check for short
        if not self.hull1h.loc[hour_ts]['overlap'] and price < daily_open:
            return "short"

        return None