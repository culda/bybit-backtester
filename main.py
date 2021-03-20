import os
import time
from dotenv import load_dotenv

from src.engine.backtester import Backtester
from src.engine.strategy import strategy

if __name__ == '__main__':
    from sys import argv
    args = argv[1:]

    load_dotenv()
    symbol = os.getenv("SYMBOL")
    api_key = os.getenv("BYBIT_PUBLIC_TRADE")
    secret = os.getenv("BYBIT_SECRET_TRADE")

    Backtester(api_key = api_key, secret = secret, symbol = symbol, strategy = strategy, args = args)
