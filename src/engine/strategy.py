'''
signal: array of indicators that all need to resolve to True for a long entry OR false for a short entry. "name" is linked to the definitions from indicators.py. You can build your own
atr: pillar of the strategy. SL and TP are defined by it.
no-trade-hours: don't trade at these hours (UTC)
tp-atr: take profit multiplier. i.e If 2, take profit at entry +/- atrx2
sl-atr: stop loss multiplier. i.e If 2, stop loss at entry +/- atrx2
risk: % of balance to risk on each trade (factors in stop-loss)
'''

strategy = {
    "signal": [
        {
            "name": "hma",
            "properties":{
                "interval": '1h',
                "length": 55,
                "offset": 2
            }
        },
        {
            "name": "aroon",
            "properties":{
                "interval": '15m',
                "length": 14,
            }
        },
    ],
    "atr": {
        "name": "atr",
        "properties":{
            "interval": '1h',
            "length": 24
        }
    },
    "no-trade-hours": [3,4,5],
    "tp-atr": 2,
    "sl-atr": 2,
    "risk": 1
}