import hashlib
import hmac
import json
import time
import urllib.parse
from threading import Thread
from collections import deque

from requests import Request, Session
from requests.exceptions import HTTPError
from websocket import WebSocketApp
import pandas as pd
import logging
from utils import get_logger

logger = get_logger(logging.getLogger(__name__), 'logs/bybit.log', logging.DEBUG)


COLS = ['Open', 'High', 'Low', 'Close', 'Volume', 'TurnOver']

class Bybit():
    url_main = 'https://api.bybit.com'
    url_test = 'https://api-testnet.bybit.com'
    ws_url_main = 'wss://stream.bybit.com/realtime'
    ws_url_test = 'wss://stream-testnet.bybit.com/realtime'
    headers = {'Content-Type': 'application/json'}

    def __init__(self, api_key, secret, symbol, ws=True, test=False):
        self.api_key = api_key
        self.secret = secret

        self.symbol = symbol
        self.klines = {}

        self.s = Session()
        self.s.headers.update(self.headers)

        self.url = self.url_main if not test else self.url_test
        self.ws_url = self.ws_url_main if not test else self.ws_url_test

        self.ws = ws
        if ws:
            self._connect()

    #
    # WebSocket
    #

    def _connect(self):
        logger.debug("init WebSocketApp")
        self.ws = WebSocketApp(url=self.ws_url,
                               on_open=self._on_open,
                               on_message=self._on_message)

        self.ws_data = {f'trade.{self.symbol}': deque(maxlen=200), 
                        f'instrument_info.100ms{self.symbol}': {}, 
                        f'orderBookL2_25.{self.symbol}': pd.DataFrame(),
                        'position': {}, 
                        'execution': deque(maxlen=200), 
                        'order': deque(maxlen=200)
                        }

        logger.debug("get positions")
        positions = self.get_position_http()['result']
        for p in positions:
            if p['symbol'] == self.symbol:
                self.ws_data['position'].update(p)
                break

        logger.debug(f"positions: {positions}")
        Thread(target=self.ws.run_forever, daemon=True).start()

    def _on_open(self):
        logger.debug("websocket is open")
        timestamp = int((time.time()+1000) * 1000)
        param_str = 'GET/realtime' + str(timestamp)
        sign = hmac.new(self.secret.encode('utf-8'),
                        param_str.encode('utf-8'), hashlib.sha256).hexdigest()

        logger.debug("authenticating...")
        self.ws.send(json.dumps(
            {'op': 'auth', 'args': [self.api_key, timestamp, sign]}))                    

        self.ws.send(json.dumps(
            {'op': 'subscribe', 'args': ['position',
                                         'execution',
                                         'order',
                                        #  f'trade.{self.symbol}',
                                         f'klineV2.1.{self.symbol}',
                                        #  f'klineV2.15.{self.symbol}',
                                        #  f'klineV2.240.{self.symbol}'
                                         ]}))


    def _on_message(self, message):
        message = json.loads(message)
        logger.debug(message)

        # if (message.success == False):
        #     self.ws.send('{"op":"ping"}')

        topic = message.get('topic')

        if topic == f'orderBookL2_25.{self.symbol}':
            self._on_ws_orderbook(message)            
        elif topic == 'execution':
            self._on_ws_execution(message)
        elif topic == 'order':
            self._on_ws_execution(message)
        elif 'instrument_info' in topic:
            self._on_ws_instrumentinfo(message)
        elif 'trade' in topic:
            self._on_ws_trade(message)
        elif topic == 'position':
            self._on_ws_position(message)
        elif 'kline' in topic:
            self._on_ws_kline(message)

    def _on_ws_execution(self, message):
        self.ws_data['execution'].append(message['data'][0])        

    def _on_ws_order(self, message):
        self.ws_data['order'].append(message['data'][0])            

    def _on_ws_instrumentinfo(self, message):
        self.ws_data[f'instrument_info.100ms.{self.symbol}'].append(message['data'][0])            

    def _on_ws_trade(self, message):
        self.ws_data[f'trade.{self.symbol}'].append(message['data'][0])        

    def _on_ws_position(self, message):
        self.ws_data['position'].append(message['data'][0])        

    def _on_ws_kline(self, message):
        try:
            data = message['data'][0]
            
            output_data = [
                data['open'],
                data['high'],
                data['low'],
                data['close'],
                data['volume'],
                data['turnover']]
                
            interval = data['end'] - data['start']

            df = pd.DataFrame([output_data], index = [data['start']], columns=COLS)

            if not str(interval) in self.klines:
                logger.debug(f'{interval}: new kline, {output_data}')
                self.klines[str(interval)] = df
            else:
                logger.debug(f'{interval}: kline update, {output_data}')
                self.klines[str(interval)].update(df)


        except Exception as e:
            logger.error(f"_on_ws_kline: {e}")

        # df['Date'] = [datetime.fromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in df['TimeStamp']]


    def _on_ws_orderbook(message):
        if message['type'] == 'snapshot':
            self.ws_data[topic] = pd.io.json.json_normalize(message['data']).set_index('id').sort_index(ascending=False)
        else: # message['type'] == 'delta'
            # delete or update or insert
            if len(message['data']['delete']) != 0:
                drop_list = [x['id'] for x in message['data']['delete']]
                self.ws_data[topic].drop(index=drop_list)
            elif len(message['data']['update']) != 0:
                update_list = pd.io.json.json_normalize(message['data']['update']).set_index('id')
                self.ws_data[topic].update(update_list)
                self.ws_data[topic] = self.ws_data[topic].sort_index(ascending=False)
            elif len(message['data']['insert']) != 0:
                insert_list = pd.io.json.json_normalize(message['data']['insert']).set_index('id')
                self.ws_data[topic].update(insert_list)
                self.ws_data[topic] = self.ws_data[topic].sort_index(ascending=False)        

    def subscribe(self, topic):
        self.ws.send(json.dumps(
            {'op': 'subscribe', 'args': [f'${topic}.${self.symbol}']}))

    def get_trade(self):
        if not self.ws: return None
        
        return self.ws_data['trade.' + str(self.symbol)]

    def get_instrument(self):
        if not self.ws: return None

        # データ待ち
        while len(self.ws_data['instrument_info.' + str(self.symbol)]) != 4:
            time.sleep(1.0)
        
        return self.ws_data['instrument_info.' + str(self.symbol)]

    def get_orderbook(self, side=None):
        if not self.ws: return None

        # データ待ち
        while self.ws_data['orderBookL2_25.' + str(self.symbol)].empty:
            time.sleep(1.0)

        if side == 'Sell':
            orderbook = self.ws_data['orderBookL2_25.' + str(self.symbol)].query('side.str.contains("Sell")', engine='python')
        elif side == 'Buy':
            orderbook = self.ws_data['orderBookL2_25.' + str(self.symbol)].query('side.str.contains("Buy")', engine='python')
        else:
            orderbook = self.ws_data['orderBookL2_25.' + str(self.symbol)]
        return orderbook

    def get_position(self):
        if not self.ws: return None
        
        return self.ws_data['position']

    def get_my_executions(self):
        if not self.ws: return None
        
        return self.ws_data['execution']

    def get_order(self):
        if not self.ws: return None
        
        return self.ws_data['order']

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

    def place_active_order(self, side=None, symbol=None, order_type=None,
                           qty=None, price=None,
                           time_in_force='GoodTillCancel', take_profit=None,
                           stop_loss=None, order_link_id=None):
        payload = {
            'side': side,
            'symbol': symbol if symbol else self.symbol,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'time_in_force': time_in_force,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'order_link_id': order_link_id
        }
        return self._request('POST', '/open-api/order/create', payload=payload)

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

    def place_active_order_v2(self, symbol=None, side=None, order_type=None,
                              qty=None, price=None,
                              time_in_force='GoodTillCancel',
                              order_link_id=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'side': side,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'time_in_force': time_in_force,
            'order_link_id': order_link_id
        }
        return self._request('POST', '/v2/private/order/create', payload=payload)

    def cancel_active_order_v2(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/v2/private/order/cancel', payload=payload)

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


if __name__ == '__main__':
    pass