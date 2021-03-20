import logging

from src.account.account import Account
from src.utils.utils import get_logger, timestamp_to_date, sameday, percent, date_to_seconds

logger = get_logger(logging.getLogger(__name__), 'logs/test-account.log', logging.DEBUG)

class TestAccount(Account):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def getResult(self):
        return {
            "trades": len(self.trades),
            "strikerate": f'{(self.totalwon / len(self.trades) * 100):.2f}%',
            "balance": self.balance,
            "growth": f'{percent(self.startbalance, self.balance):.2f}%',
            "maxdrawdown": f'{self.maxdrawdown:.2f}%',
            "won": self.totalwon,
            "lost": self.totallost,
            "even": self.totaleven,
        }

    def get_last_trade(self):
        return self.trades[ len(self.trades) -1 ] if len(self.trades) else None

    #  At given price, closes a portion of the position (1.0 == 100%, 0.5 == 50%) using a market order
    
    def takeprofits( self, price, portion, timestamp ):

        if not (self.trade and self.trade["size"]):
            return
        
        #  TODO: round()? for contracts / XBT sizing
        quantity = self.trade["size"] * portion

        self.trade["size"] -= quantity

        pnl = self._calc_pnl_xbt( self.trade["side"], self.trade["entry"], price, quantity )

        pnl -= quantity * self.fees["taker"] * 2
        
        self.balance += pnl

        self.trade.takeprofits.append({
            "timestamp": timestamp,
            "price": price,
            "portion": portion,
            "size": quantity,
            "profit": pnl
        })


    def open(self, side, price, stop = None, tp = None, risk = 5, is_maker = False, timestamp = None ):

        self.dailytrades += 1

        size = self._size_by_stop_risk( risk, price, stop ) if stop else ( self.balance * ( risk / 100 ) )
        
        pnl = 0

        if is_maker:
            pnl += size / price * self.fees["maker"]
        else:
            pnl -= size / price * self.fees["taker"]

        self.trade = {
            "side": side,
            "entry": price,
            "stop": stop,
            "tp": tp,
            "risk": risk,
            "size": size,
            "pnl": pnl,
            "takeprofits": [],
            "opentimestamp": timestamp,
            "closetimestamp": None,
            "result": {},
            "meta": { "initialstop": stop }
        }

    def close( self, price, is_maker = True, timestamp = None):
        logger.info(f"close: {price}, is_maker = {is_maker}")
        logger.info(f"close: active trade: {self.trade}")
        
        if not self.trade:
            logger.debug("close: nothing to close")
            return None

        self._close_position( price, is_maker = is_maker, timestamp = timestamp, stopped = None )

    def _close_position( self, price, is_maker = False, timestamp = None, stopped = False ):
                        
        self.trade["closetimestamp"] = timestamp
        self.trade["exit"] = price

        pnl = self.trade["pnl"] + self._calc_pnl_xbt( self.trade["side"], self.trade["entry"], self.trade["exit"], self.trade["size"] )

        if is_maker:
            pnl += self.trade["size"] / price * self.fees["maker"]
        else:
            pnl -= self.trade["size"] / price * self.fees["taker"]

        # if self.fees["on"]:
        #     if self.fees["mode"] == 'taker':
        #         pnl -= self.trade["size"] / self.trade["entry"] * self.fees["taker"] * 2
        #     elif self.fees["mode"] == 'maker': 
        #         pnl += self.trade["size"] / self.trade["entry"] * self.fees["maker"] * 2
        #     elif self.fees["mode"] == 'makertaker':
        #         pnl -= self.trade["size"] / self.trade["entry"] * self.fees["taker"]
        #         pnl += self.trade["size"] / self.trade["entry"] * self.fees["maker"]

        startbal = self.balance

        self.balance += pnl

        self.closed = True        
        self.won = pnl > 0
        self.lost = pnl < 0
        self.even = pnl == 0

        self.maxbalance = max(self.balance, self.maxbalance)
        self.maxdrawdown = min(self.maxdrawdown, percent(self.maxbalance, self.balance))        

        if self.won: 
            self.dailywon+=1
            self.totalwon+=1
        if self.lost: 
            self.dailylost+=1
            self.totallost+=1
        if self.even:
            self.dailyeven+=1
            self.totaleven+=1

        self.trade["result"] = {
            "stopped": self.stopped,
            "exit": self.trade["exit"],
            "profit": pnl,
            "percent": percent( startbal, self.balance ),
            "balance": { "before": startbal, "after": self.balance }
        }

        self.trades.append( self.trade )

        self.trade = None

    def tightenstop( self, price ):

        if self.trade and self.trade["side"] == 'long':
            self.trade["stop"] = max( self.trade["stop"], price )
        elif self.trade and self.trade["side"] == 'short':
            self.trade["stop"] = min( self.trade["stop"], price )
            
    #  Check for stop outs etc.
    def update( self, timestamp, kline ):
        
        #  Test if self is new day to reset intraday statistics
        if self.lastbardate:
            if  not sameday( self.lastbardate, timestamp ):
                self.dailywon = 0
                self.dailylost = 0
                self.dailytrades = 0
                self.dailyeven = 0

        self.lastbardate = timestamp

        self.stopped = False
        self.closed = False
        self.lost = False
        self.won = False
        self.even = False
            
        if not self.trade:
            return
        
        if self.trade["side"] == 'long':
            if float(kline["Low"]) <= self.trade["stop"]:
                logger.info(f"{timestamp_to_date(timestamp).strftime('%Y-%m-%d %H:%M:%S.%d')}: close LONG at SL")
                self.stopped = True
                self._close_position( self.trade["stop"], is_maker = False, timestamp = timestamp )
            elif float(kline["High"]) >= self.trade["tp"]:
                logger.info(f"{timestamp_to_date(timestamp).strftime('%Y-%m-%d %H:%M:%S.%d')}: close LONG at TP")
                self._close_position( self.trade["tp"], is_maker = True, timestamp = timestamp )
        elif self.trade["side"] == 'short':
            if float(kline["High"]) >= self.trade["stop"]:
                logger.info(f"{timestamp_to_date(timestamp).strftime('%Y-%m-%d %H:%M:%S.%d')}: close SHORT at SL")
                self.stopped = True
                self._close_position( self.trade["stop"], is_maker = False, timestamp = timestamp )
            elif float(kline["Low"]) <= self.trade["tp"]:
                logger.info(f"{timestamp_to_date(timestamp).strftime('%Y-%m-%d %H:%M:%S.%d')}: close SHORT at TP")
                self._close_position( self.trade["tp"], is_maker = True, timestamp = timestamp )
