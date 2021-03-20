#%%

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import matplotlib.cbook as cbook

from src.utils.utils import timestamp_to_date

class Chart():
    def __init__(self, **kwargs):
        account = kwargs['account']
        trades = account.trades
        risk = kwargs['risk']
        df = pd.DataFrame({'balance': [t['result']['balance']['after'] for t in trades]}, index = [timestamp_to_date(t['closetimestamp'])  for t in trades])

        title = f"Risk: {risk};"

        ax = df.plot(figsize=(8, 4))
        ax.set(xlabel='time', ylabel='balance', title=title)
        ax.grid()

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))        

        plt.gcf().autofmt_xdate()
        plt.gcf().savefig("chart.png")
        plt.show()


if __name__ == "__main__":
    # Data for plotting

    data = cbook.get_sample_data('goog.npz', np_load=True)['price_data']

    trades = [{'side': 'short', 'entry': 7159.5, 'stop': 7174.0, 'tp': 7145.73, 'risk': 5, 'size': 24.687931034482762, 'takeprofits': [], 'opentimestamp': 1577836860, 'closetimestamp': 1577841900, 'result': {'stopped': True, 'exit': 7174.0, 'profit': -0.06224283774934391, 'percent': -6.224283774934392, 'balance': {'before': 1, 'after': 0.9377571622506561}}, 'meta': {'initialstop': 7174.0}, 'exit': 7174.0}, {'side': 'short', 'entry': 7168.5, 'stop': 7190.62, 'tp': 7147.48, 'risk': 5, 'size': 15.195099949353212, 'takeprofits': [], 'opentimestamp': 1577919900, 'closetimestamp': 1577930460, 'result': {'stopped': False, 'exit': 7147.48, 'profit': 0.03708963823508135, 'percent': 3.955143157324942, 'balance': {'before': 0.9377571622506561, 'after': 0.9748468004857375}}, 'meta': {'initialstop': 7190.62}, 'exit': 7147.48}, {'side': 'short', 'entry': 6945.0, 'stop': 6980.42, 'tp': 6911.35, 'risk': 5, 'size': 9.557186659194569, 'takeprofits': [], 'opentimestamp': 1578009720, 'closetimestamp': 1578012300, 'result': {'stopped': False, 'exit': 6911.35, 'profit': 0.041753700928723825, 'percent': 4.283103858772386, 'balance': {'before': 0.9748468004857375, 'after': 1.0166005014144612}}, 'meta': {'initialstop': 6980.42}, 'exit': 6911.35}, {'side': 'short', 'entry': 7303.5, 'stop': 7352.32, 'tp': 7257.12, 'risk': 5, 'size': 7.604200903400822, 'takeprofits': [], 'opentimestamp': 1578135600, 'closetimestamp': 1578162960, 'result': {'stopped': True, 'exit': 7352.32, 'profit': -0.054294354294989085, 'percent': -5.340775872080121, 'balance': {'before': 1.0166005014144612, 'after': 0.9623061471194722}}, 'meta': {'initialstop': 7352.32}, 'exit': 7352.32}, {'side': 'short', 'entry': 7292.5, 'stop': 7341.08, 'tp': 7246.34, 'risk': 5, 'size': 7.222743493072006, 'takeprofits': [], 'opentimestamp': 1578164400, 'closetimestamp': 1578173460, 'result': {'stopped': True, 'exit': 7341.08, 'profit': -0.05140840324860453, 'percent': -5.342208755757024, 'balance': {'before': 0.9623061471194722, 'after': 0.9108977438708676}}, 'meta': {'initialstop': 7341.08}, 'exit': 7341.08}, {'side': 'short', 'entry': 7336.5, 'stop': 7383.72, 'tp': 7291.64, 'risk': 5, 'size': 7.076240256150555, 'takeprofits': [], 'opentimestamp': 1578175140, 'closetimestamp': 1578183600, 'result': {'stopped': True, 'exit': 7383.72, 'profit': -0.048791883317378604, 'percent': -5.3564611006760305, 'balance': {'before': 0.9108977438708676, 'after': 0.862105860553489}}, 'meta': {'initialstop': 7383.72}, 'exit': 7383.72}, {'side': 'long', 'entry': 7422.0, 'stop': 7380.61, 'tp': 7461.32, 'risk': 5, 'size': 7.729584074689472, 'takeprofits': [], 'opentimestamp': 1578225600, 'closetimestamp': 1578238380, 'result': {'stopped': False, 'exit': 7461.32, 'profit': 0.036868937228250964, 'percent': 4.27661368692939, 'balance': {'before': 0.862105860553489, 'after': 0.8989747977817399}}, 'meta': {'initialstop': 7380.61}, 'exit': 7461.32}, {'side': 'short', 'entry': 7346.0, 'stop': 7385.06, 'tp': 7308.89, 'risk': 5, 'size': 8.453493170128768, 'takeprofits': [], 'opentimestamp': 1578268860, 'closetimestamp': 1578275400, 'result': {'stopped': True, 'exit': 7385.06, 'profit': -0.04893749025393984, 'percent': -5.443699909574253, 'balance': {'before': 0.8989747977817399, 'after': 0.8500373075278}}, 'meta': {'initialstop': 7385.06}, 'exit': 7385.06}, {'side': 'long', 'entry': 7541.5, 'stop': 7496.54, 'tp': 7584.21, 'risk': 5, 'size': 7.129177440748331, 'takeprofits': [], 'opentimestamp': 1578321900, 'closetimestamp': 1578346080, 'result': {'stopped': False, 'exit': 7584.21, 'profit': 0.03658315437642186, 'percent': 4.303711619766226, 'balance': {'before': 0.8500373075278, 'after': 0.886620461904222}}, 'meta': {'initialstop': 7496.54}, 'exit': 7584.21}, {'side': 'long', 'entry': 7849.5, 'stop': 7793.5, 'tp': 7902.7, 'risk': 5, 'size': 6.213863674747492, 'takeprofits': [], 'opentimestamp': 1578374100, 'closetimestamp': 1578395640, 'result': {'stopped': False, 'exit': 7902.7, 'profit': 0.038724268314613, 'percent': 4.367626281875297, 'balance': {'before': 0.886620461904222, 'after': 0.9253447302188349}}, 'meta': {'initialstop': 7793.5}, 'exit': 7902.7}]

    df = pd.DataFrame({'balance': [t['result']['balance']['after'] for t in trades]}, index = [timestamp_to_date(t['closetimestamp'])  for t in trades])

    # index = pd.date_range(start = "2020-03-01", end = "2020-09-30", freq = "D")
    # index = [pd.to_datetime(date, format='%Y-%m-%d').date() for date in index]
    # data = np.random.randint(1,100, size=len(index))
    # df = pd.DataFrame(data=data,index=index, columns=['data'])
    
    print (df.head())

    ax = df.plot()
    # set monthly locator
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    # set formatter
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    # set font and rotation for date tick labels
    plt.gcf().autofmt_xdate()

    plt.gcf().savefig("test.png")
    plt.show()
# %%
