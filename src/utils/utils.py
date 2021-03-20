import json
import logging
import dateparser
import pytz
from decimal import Decimal
from datetime import datetime
from pandas import Series

from src.utils.constants import *

def get_logger(logger, fname, level = logging.INFO):
    fh = logging.FileHandler(fname)
    fh.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    return logger

logger = get_logger(logging.getLogger(__name__), 'logs/utils.log')

def fwrite(fname, data, operation):
    with open(fname, operation) as f:
        f.write(json.dumps(data))

def async_request(method, *args, callback=None, timeout=15, **kwargs):
    """Makes request on a different thread, and optionally passes response to a
    `callback` function when request returns.
    """
    if callback:
        def callback_with_args(response, *args, **kwargs):
            callback(response)
        kwargs['hooks'] = {'response': callback_with_args}
    kwargs['timeout'] = timeout
    thread = Thread(target=method, args=args, kwargs=kwargs)
    thread.start()

def date_to_seconds(date_str):
    """Convert UTC date to seconds

    If using offset strings add "UTC" to date string e.g. "now UTC", "11 hours ago UTC"

    See dateparse docs for formats http://dateparser.readthedocs.io/en/latest/

    :param date_str: date in readable format, i.e. "January 01, 2018", "11 hours ago UTC", "now UTC"
    :type date_str: str
    """
    # get epoch value in UTC
    epoch = datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    # parse our date string
    d = dateparser.parse(date_str)
    # if the date is not timezone aware apply UTC timezone
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d = d.replace(tzinfo=pytz.utc)

    # return the difference in time
    return int((d - epoch).total_seconds())


def interval_to_milliseconds(interval):
    """Convert a Binance interval string to milliseconds

    :param interval: Binance interval string 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
    :type interval: str

    :return:
         None if unit not one of m, h, d or w
         None if string not in correct format
         int value of interval in milliseconds
    """
    ms = None
    seconds_per_unit = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60
    }

    unit = interval[-1]
    if unit in seconds_per_unit:
        try:
            ms = int(interval[:-1]) * seconds_per_unit[unit] * 1000
        except ValueError:
            pass
    return ms

def timestamp_to_date(timestamp):    
    return datetime.fromtimestamp(timestamp)

def verify_series(series: Series) -> Series:
    """If a Pandas Series return it."""
    if series is not None and isinstance(series, Series):
        return series

def get_offset(x: int) -> int:
    """Returns an int, otherwise defaults to zero."""
    return int(x) if isinstance(x, int) else 0

def start_of_hour(ts):
    dt = datetime.fromtimestamp(int(ts))
    return dt.minute == 0

def start_of_hour4(ts):
    dt = datetime.fromtimestamp(int(ts))
    return dt.minute == 0 and dt.hour %4 == 0

def start_of_min15(ts):
    dt = datetime.fromtimestamp(int(ts))
    return dt.minute %15 == 0

def start_of_day(ts):
    dt = datetime.fromtimestamp(int(ts))
    return dt.hour == 0 and dt.minute == 0

def sameday(first, second):
    dtf = datetime.fromtimestamp(int(first))
    dts = datetime.fromtimestamp(int(second))

    return dtf.year == dts.year and dtf.month == dts.month and dtf.day == dts.day

def percent( f, t ):
    return ((t - f) / f) * 100

def interval_bybit_notation(interval):
    return {
        '1m': 1,
        '3m': 3,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h' : 60,
        '2h': 120,
        '4h': 240,
        'D' : 'D'
    }[interval]
