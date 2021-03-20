import logging
from src.utils.utils import get_logger
logger = get_logger(logging.getLogger(__name__), 'logs/account.log', logging.DEBUG)

class Account():

    def __init__(self, *args, **kwargs):
        self.fees = {
            "on": True,
            "taker": 0.075 / 100,         
            "maker": 0.025 / 100,          
            "mode": 'makertaker'
        }
        
        self.stopped = False
        self.closed =  False
        self.lost = False
        self.won = False
        self.even = False
    
        self.balance = kwargs.get("startbalance", 1)

        self.startbalance = self.balance
        self.maxbalance = self.startbalance

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
        
        self.maxdrawdown = 0

    def _calc_pnl_xbt( self, side, entry, exit, size ):
        exit1 = 1 / float(exit)
        entry1 = 1 / float(entry)
        return ( exit1 - entry1 ) * size if side == 'short' else ( entry1 - exit1 ) * size 

    def _size_by_stop_risk( self, risk, entry, stop ):
        if not stop:
            stop = entry * 0.98
        size_risk = self.balance * ( risk / 100 )
        stop1 = 1 / float(stop)
        entry1 = 1 / float(entry)
        if stop < entry:
            return size_risk / abs( entry1 - stop1 )
        else:
            return size_risk / abs( stop1 - entry1 )