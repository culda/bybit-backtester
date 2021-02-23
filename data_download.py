import os
from ems_bybit import Bybit
from constants import BYBIT_PUBLIC_TRADE, BYBIT_SECRET_TRADE, PATH_HIST_1M, PATH_HIST_1H
from tick_service import get_historical_klines_pd

def main():
    dirname = os.path.dirname(__file__)
    
    # 1m
    filename = os.path.join(dirname, PATH_HIST_1M)
    bybit = Bybit(BYBIT_PUBLIC_TRADE, BYBIT_SECRET_TRADE, 'BTCUSD', True)
    df = get_historical_klines_pd(bybit, 'BTCUSD', 1, '1609459200')
    df.to_csv(filename)


    # 1h
    filename = os.path.join(dirname, PATH_HIST_1H)
    bybit = Bybit(BYBIT_PUBLIC_TRADE, BYBIT_SECRET_TRADE, 'BTCUSD', True)
    df = get_historical_klines_pd(bybit, 'BTCUSD', 60, '1609459200')
    df.to_csv(filename)
    

if __name__ == "__main__":
    main()