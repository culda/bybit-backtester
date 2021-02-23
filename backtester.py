import logging
from utils import get_logger
from utils import sameday, percent

logger = get_logger(logging.getLogger(__name__), 'logs/tick_service.log', logging.DEBUG)

class Backtester():

    def __init__(self, *args, **kwargs):
        self.fees = {
            "on": True,
            "taker": 0.075 / 100,         # Bybit taker fees = 0.075%
            "maker": 0.025 / 100,          
            "mode": 'makertaker'          # 'makertaker': one of each, 'maker': limit orders both sides, 'taker': market orders both sides
        }
        
        self.stopped = False
        self.closed =  False
        self.lost = False
        self.won = False
        self.even = False

        self.balance = 1
        self.startbalance = self.balance
        self.trade = None
        self.trades = []

        self.dailywon = 0
        self.dailylost = 0
        self.dailytrades = 0
        self.dailyeven = 0

        self.lastbardate = None

        self.totalwon = 0
        self.totallost = 0
        self.totaleven = 0

    def open(self, side, price, stop, tp, risk, timestamp ):

        self.dailytrades += 1

        #  Close any open trades
        if self.trade:
            self._close_position( price, timestamp, False )

        self.trade = {
            "side": side,
            "entry": price,
            "stop": stop,
            "tp": tp,
            "risk": risk,
            "size": self._size_by_stop_risk( risk, price, stop ) if stop else ( self. balance * ( risk / 100 ) ) ,
            "takeprofits": [],
            "opentimestamp": timestamp,
            "closetimestamp": None,
            "result": {},
            "meta": { "initialstop": stop }
        }

    def getResult(self):

        return {
            "trades": len(self.trades),
            "strikerate": f'{(self.totalwon / len(self.trades) * 100):.2f}%',
            "balance": self.balance,
            "growth": f'{percent(self.startbalance, self.balance):.2f}%',
            "won": self.totalwon,
            "lost": self.totallost,
            "even": self.totaleven,
        }

    def getLasttrade(self):
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

    def close( self, price, timestamp ):

        if not self.trade:
            return None

        self._close_position( price, timestamp, False )

    def tightenstop( self, price ):

        if self.trade and self.trade["side"] == 'long':
            self.trade["stop"] = max( self.trade["stop"], price )
        elif self.trade and self.trade["side"] == 'short':
            self.trade["stop"] = min( self.trade["stop"], price )
            
    #  Check for stop outs etc.
    def update( self, timestamp, kline ):
        
        # d = new Date( Date.parse( bar.opentimestamp ) )
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
            
        if not (self.trade and self.trade["stop"]):
            return
        
        if self.trade["side"] == 'long':
            if float(kline["Low"]) <= self.trade["stop"]:
                print("closing at stop: ", self.trade)
                self._close_position( self.trade["stop"], timestamp, True )
            elif float(kline["High"]) >= self.trade["tp"]:
                print("closing at tp: ", self.trade)
                self._close_position( self.trade["tp"], timestamp, False )
        elif self.trade["side"] == 'short':
            if float(kline["High"]) >= self.trade["stop"]:
                print("closing at stop: ", self.trade)
                self._close_position( self.trade["stop"], timestamp, True )
            elif float(kline["Low"]) <= self.trade["tp"]:
                print("closing at stop: ", self.trade)
                self._close_position( self.trade["tp"], timestamp, False )


    def _close_position( self, price, timestamp, stopped=False ):
                        
        self.trade["closetimestamp"] = timestamp
        self.trade["exit"] = price

        pnl = self._calc_pnl_xbt( self.trade["side"], self.trade["entry"], self.trade["exit"], self.trade["size"] )

        if self.fees["on"]:
            if self.fees["mode"] == 'taker':
                pnl -= self.trade["size"] * self.fees["taker"] * 2
            elif self.fees["mode"] == 'maker': 
                pnl += self.trade["size"] * self.fees["maker"] * 2
            elif self.fees["mode"] == 'makertaker':
                pnl -= self.trade["size"] * self.fees["taker"]
                pnl += self.trade["size"] * self.fees["maker"]

        startbal = self.balance

        self.balance += pnl

        self.closed = True
        self.stopped = stopped
        self.won = pnl > 0
        self.lost = pnl < 0
        self.even = pnl == 0

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
            "stopped": stopped,
            "exit": self.trade["exit"],
            "profit": pnl,
            "percent": percent( startbal, self.balance ),
            "balance": { "before": startbal, "after": self.balance }
        }

        self.trades.append( self.trade )

        self.trade = None

    def _calc_pnl_xbt( self, side, entry, exit, size ):
        contracts = round( size * entry )
        exit1 = 1 / float(exit)
        entry1 = 1 / float(entry)
        return ( exit1 - entry1 ) * contracts if side == 'short' else ( entry1 - exit1 ) * contracts 

    def _size_by_stop_risk( self, risk, entry, stop ):
        size_risk = self.balance * ( risk / 100 )
        rang = abs( entry - stop )
        return entry * ( size_risk / rang )

