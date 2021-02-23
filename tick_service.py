import os
import time
import pandas as pd 
from datetime import datetime
from utils import date_to_seconds, get_logger, PATH_HIST_KLINES
import logging

logger = get_logger(logging.getLogger(__name__), 'logs/tick_service.log', logging.DEBUG)

def get_bybit_hist_klines(bybit, symbol, interval, start_str, end_str=None):
    """Get Historical Klines from Bybit 
    :param symbol: Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
    :type symbol: str
    :param interval: Bybit Kline interval -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
    :type interval: str
    :param start_str: Start date string in UTC format
    :type start_str: str
    :param end_str: optional - end date string in UTC format
    :type end_str: str
    :return: list of OHLCV values
    """

    limit = 200
    start_ts = int(date_to_seconds(start_str))
    end_ts = None
    if end_str:
        end_ts = int(date_to_seconds(end_str))
    else: 
        end_ts = int(date_to_seconds('now'))

    output_data = []
    indexes = []

    idx = 0
    symbol_existed = False
    while True:
        # fetch the klines from start_ts up to max 200 entries 
        temp_dict = bybit.kline(symbol=symbol, interval=str(interval), _from=start_ts, limit=limit)

        # handle the case where our start date is before the symbol pair listed on Binance
        if not symbol_existed and len(temp_dict):
            symbol_existed = True

        if symbol_existed:
            # extract data and convert to list 
            temp_data = []
            for i in temp_dict['result']:
                l = list(i.values())[3:]
                temp_data += [list(float(k) for k in l)]

            output_data += temp_data

            # add timestamps to a different list to create indexes later
            temp_data = [int(list(i.values())[2]) for i in temp_dict['result']]
            indexes += temp_data

            # move start_ts over by one interval atter the last value in the array
            # NOTE: current implementation does not support inteval of D/W/M/Y
            start_ts = temp_dict['result'][len(temp_dict['result'])-1]['open_time'] + interval * 60

        else:
            # try every interval until data is found
            start_ts += interval

        idx += 1
        # if we received less than the required limit, we reached present time, so exit the loop
        if len(temp_data) < limit:
            break

        # sleep after every 3rd call to be kind to the API
        if idx % 3 == 0:
            time.sleep(0.2)

    # convert to data frame 
    df = pd.DataFrame(output_data, index = indexes, columns=['Open', 'High', 'Low', 'Close', 'Volume', 'TurnOver'])
    df.loc[:,'Date'] = [datetime.fromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in df.index]

    return df

def aggregate_local_and_hist_klines(bybit, symbol, intervals):
    """Aggregate local klines with bybit klines
    :param symbol: Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
    :type symbol: str
    :param intervals: array of Bybit Kline intervals -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
    :type intervals: []
    :return: dict of pandas Dataframes, containing OHLCV values
    """    
    dirname = os.path.dirname(__file__)

    result = {}

    for interval in intervals:
        filename = os.path.join(dirname, PATH_HIST_KLINES[interval])
        file_klines = pd.read_csv(filename, index_col=0)
        file_klines.loc[:,'Date'] = [datetime.fromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in file_klines.index]

        last = file_klines.tail(1).index[0]
        next_ts = int(last) + interval_bybit_notation(interval)
        if next_ts < int(datetime.now().timestamp()):
            bybit_klines = get_bybit_hist_klines(bybit, symbol, interval_bybit_notation(interval), str(next_ts))

        result[interval] = pd.concat([file_klines, bybit_klines]) if not len(bybit_klines.index) == 0 else file_klines
    
    return result

def interval_bybit_notation(interval):
    conversion = {
        '1m': 1,
        '3m': 3,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h' : 60,
        '2h': 120,
        '4h': 240,
        'D' : 'D'
    }
    return conversion[interval]