# Bybit Backtester


Running using docker commands
```
git clone https://github.com/culda/bybit-backtester.git
cd bybit-backtester

docker build -f dockerfile -t backtester:1.0 .
docker run -d backtester:1.0
```

Non-docker

```
>>> python3 -V
3.7+
```

```
git clone https://github.com/culda/bybit-backtester.git
cd bybit-backtester
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p logs trades hist_data
```

You need to create a .env file and fill in your API keys
```
SYMBOL=BTCUSD
BYBIT_PUBLIC_TRADE=
BYBIT_SECRET_TRADE=

```

Non-docker command

```
python main.py backtester 2021-03-05 2021-03-10
```


Running tests (if you're into unit tests)
```
python -m unittest discover -s src/tests -p '*_test.py'
```