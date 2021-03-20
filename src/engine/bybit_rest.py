import hashlib
import hmac
import json
import time
import urllib.parse
from collections import deque
import pandas as pd
from requests import Request, Session
from requests.exceptions import HTTPError
import logging

from src.utils.utils import get_logger, date_to_seconds

logger = get_logger(logging.getLogger(__name__), 'logs/bybit.log', logging.DEBUG)

class BybitRest():
    url_main = 'https://api.bybit.com'
    url_test = 'https://api-testnet.bybit.com'
    headers = {'Content-Type': 'application/json'}

    def __init__(self, api_key, secret, symbol, test = False):
        self.api_key = api_key
        self.secret = secret

        self.symbol = symbol
    
        self.s = Session()
        self.s.headers.update(self.headers)

        self.url = self.url_main if not test else self.url_test

    #
    # Http Apis
    #

    def _request(self, method, path, payload):
        payload['api_key'] = self.api_key
        payload['timestamp'] = int(time.time() * 1000)
        payload = dict(sorted(payload.items()))
        for k, v in list(payload.items()):
            if v is None:
                del payload[k]

        param_str = urllib.parse.urlencode(payload)
        sign = hmac.new(self.secret.encode('utf-8'),
                        param_str.encode('utf-8'), hashlib.sha256).hexdigest()
        payload['sign'] = sign

        if method == 'GET':
            query = payload
            body = None
        else:
            query = None
            body = json.dumps(payload)


        req = Request(method, self.url + path, data=body, params=query)
        prepped = self.s.prepare_request(req)

        resp = None
        try:
            resp = self.s.send(prepped)
            resp.raise_for_status()
        except HTTPError as e:
            print(e)

        try:
            return resp.json()
        except json.decoder.JSONDecodeError as e:
            print('json.decoder.JSONDecodeError: ' + str(e))
            return resp.text

    def get_hist_klines(self, symbol, interval, start_str, end_str=None):
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
            temp_dict = self.kline(symbol=symbol, interval=str(interval), _from=start_ts, limit=limit)

            # handle the case where our start date is before the symbol pair listed on Binance
            if not symbol_existed and len(temp_dict):
                symbol_existed = True

            if symbol_existed and len(temp_dict) > 0:
                # extract data and convert to list 
                temp_data = []
                for i in temp_dict['result']:
                    l = list(i.values())[2:]
                    temp_data += [list(float(k) for k in l)]

                output_data += temp_data

                # add timestamps to a different list to create indexes later
                # temp_data = [int(list(i.values())[2]) for i in temp_dict['result']]
                # indexes += temp_data

                # move start_ts over by one interval atter the last value in the array
                # NOTE: current implementation does not support inteval of D/W/M/Y
                start_ts = temp_dict['result'][len(temp_dict['result'])-1]['open_time'] + interval

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

        return output_data

    def get_active_order(self, order_id=None, order_link_id=None, symbol=None,
                         sort=None, order=None, page=None, limit=None,
                         order_status=None):
        payload = {
            'order_id': order_id,
            'order_link_id': order_link_id,
            'symbol': symbol if symbol else self.symbol,
            'sort': sort,
            'order': order,
            'page': page,
            'limit': limit,
            'order_status': order_status
        }
        return self._request('GET', '/open-api/order/list', payload=payload)

    def cancel_active_order(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/open-api/order/cancel', payload=payload)

    def place_conditional_order(self, side=None, symbol=None, order_type=None,
                                qty=None, price=None, base_price=None,
                                stop_px=None, time_in_force='GoodTillCancel',
                                close_on_trigger=None, reduce_only=None,
                                order_link_id=None):
        payload = {
            'side': side,
            'symbol': symbol if symbol else self.symbol,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'base_price': base_price,
            'stop_px': stop_px,
            'time_in_force': time_in_force,
            'close_on_trigger': close_on_trigger,
            'reduce_only': reduce_only,
            'order_link_id': order_link_id
        }
        return self._request('POST', '/open-api/stop-order/create', payload=payload)

    def get_conditional_order(self, stop_order_id=None, order_link_id=None,
                              symbol=None, sort=None, order=None, page=None,
                              limit=None):
        payload = {
            'stop_order_id': stop_order_id,
            'order_link_id': order_link_id,
            'symbol': symbol if symbol else self.symbol,
            'sort': sort,
            'order': order,
            'page': page,
            'limit': limit
        }
        return self._request('GET', '/open-api/stop-order/list', payload=payload)

    def cancel_conditional_order(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/open-api/stop-order/cancel', payload=payload)

    def get_leverage(self):
        payload = {}
        return self._request('GET', '/user/leverage', payload=payload)

    def change_leverage(self, symbol=None, leverage=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'leverage': leverage
        }
        return self._request('POST', '/user/leverage/save', payload=payload)

    def get_position_http(self):
        payload = {}
        return self._request('GET', '/position/list', payload=payload)

    def change_position_margin(self, symbol=None, margin=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'margin': margin
        }
        return self._request('POST', '/position/change-position-margin', payload=payload)

    def get_prev_funding_rate(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/open-api/funding/prev-funding-rate', payload=payload)

    def get_prev_funding(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/open-api/funding/prev-funding', payload=payload)

    def get_predicted_funding(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/open-api/funding/predicted-funding', payload=payload)

    def get_my_execution(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('GET', '/v2/private/execution/list', payload=payload)


    def get_balance(self, symbol = 'BTC'):
        payload = {
            'coin': symbol
        }
        return self._request('GET', '/v2/private/wallet/balance', payload=payload)        
    #
    # New Http Apis (developing)
    #

    def symbols(self):
        payload = {}
        return self._request('GET', '/v2/public/symbols', payload=payload)

    def kline(self, symbol=None, interval=None, _from=None, limit=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'interval': interval,
            'from': _from,
            'limit': limit
        }
        return self._request('GET', '/v2/public/kline/list', payload=payload)

    def place_active_order(self, symbol=None, side=None, order_type=None,
                              qty=None, price=None, stop_loss = None, reduce_only = "False",
                              time_in_force='GoodTillCancel',
                              order_link_id=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'side': side,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'time_in_force': time_in_force,
            'stop_loss': stop_loss,
            # 'reduce_only': reduce_only, #not working
            'order_link_id': order_link_id
        }
        return self._request('POST', '/v2/private/order/create', payload=payload)

    def cancel_active_order(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/v2/private/order/cancel', payload=payload)

    def cancel_active_orders_all(self):
        payload = {
            'symbol': self.symbol
        }
        return self._request('POST', '/v2/private/order/cancelAll', payload=payload)

    #
    # New Http Apis added by ST 
    #

    def get_ticker(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/v2/public/tickers', payload=payload)

    def get_orderbook_http(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/v2/public/orderBook/L2', payload=payload)
