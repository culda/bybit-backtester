import unittest

class TestTestAccount(unittest.TestCase):
    def setUp(self):
        from src.account.test_account import TestAccount
        self.account = TestAccount(startbalance=1)

    def test_trade1(self):
        self.account.open("long", 50000, stop = 49000, tp = 51000, risk = 5)
        self.assertEqual(int(self.account.trade['size']), 122500)
        self.assertEqual(self.account.trade['side'], 'long')
        self.assertEqual(self.account.trade['entry'], 50000)
        self.assertEqual(f"{self.account.trade['pnl']:.8f}", "-0.00183750")

    def test_trade2(self):
        self.account.open("long", 50000, 49000, 51000, 5)
        self.account.close(51000)
        self.assertEqual(len(self.account.trades), 1)
        self.assertEqual(self.account.trades[0]['exit'], 51000)
        self.assertEqual(f"{self.account.trades[0]['result']['profit']:.8f}", "0.04680221")

        self.assertEqual(f"{self.account.balance:.8f}", "1.04680221")

        from src.utils.utils import percent
        self.assertEqual(f'{percent(self.account.startbalance, self.account.balance):.2f}%', '4.68%')

    def test_trade3(self):
        self.account.open("long", 10000, 8000, 12000, 5)
        self.assertEqual(int(self.account.trade['size']), 2000)
        self.account.close(8000)
        self.assertEqual(len(self.account.trades), 1)
        self.assertEqual(self.account.trades[0]['exit'], 8000)
        self.assertEqual(self.account.trades[0]['exit'], 8000)
        self.assertEqual(f"{self.account.trades[0]['result']['profit']:.8f}", "-0.05008750")

        self.assertEqual(f"{self.account.balance:.8f}", "0.94991250")

        from src.utils.utils import percent
        self.assertEqual(f'{percent(self.account.startbalance, self.account.balance):.2f}%', '-5.01%')

if __name__ == '__main__':
    unittest.main()