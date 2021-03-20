import pandas_ta as ta
import pandas as pd
import numpy as np
import math
import logging

from src.utils.utils import get_logger
logger = get_logger(logging.getLogger(__name__), 'logs/indicators.log', logging.DEBUG)

def calc_indi(indi_obj, klines):
    try:
        name = indi_obj.get("name")
        props = indi_obj.get("properties")
        return globals()[f'{name}'](props,klines)
    except Exception as err:
        logger.error(f"calc_indi: {err}")

def hma(props, klines):
    interval = props.get('interval')
    length = props.get('length')
    offset = props.get('offset')
    hma = pd.DataFrame({'hma' : ta.hma(klines[interval]['Close'], length) , 'hmao': ta.hma(klines[interval]['Close'], length, offset)})
    return interval, pd.Series(hma.apply(lambda row: row['hma'] > row['hmao'] if not (math.isnan(row['hma']) or math.isnan(row['hmao'])) else None, axis = 1), name ='hma')

def aroon(props, klines):
    interval = props.get('interval')
    length = props.get('length')
    aroon = ta.aroon(klines[interval]['High'], klines[interval]['Low'], length)
    return interval, pd.Series(aroon.apply(lambda row: row[f'AROONOSC_{length}'] > 0 if not math.isnan(row[f'AROONOSC_{length}']) else None, axis = 1), name = 'aroon')

def ao(props, klines):
    interval = props.get('interval')
    fast = props.get('fast')
    slow = props.get('slow')
    offset = props.get('offset')
    ao = pd.DataFrame({'ao': ta.ao(klines[interval]['High'], klines[interval]['Low'], fast, slow), 'aoo': ta.ao(klines[interval]['High'], klines[interval]['Low'], fast, slow, offset)})
    return interval, pd.Series(ao.apply(lambda row: row['ao'] > row['aoo'] if not (math.isnan(row['ao']) or math.isnan(row['aoo'])) else None, axis = 1), name ='ao')

def atr(props, klines):
    interval = props.get('interval')
    length = props.get('length')
    return interval, pd.Series(ta.atr(klines['1h']['High'], klines['1h']['Low'], klines['1h']['Close'], 24), name = 'atr')
