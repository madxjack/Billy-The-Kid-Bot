import ccxt
from dotenv import load_dotenv
import os
from os.path import join, dirname

class Exchange:
    def __init__(self, pair) -> None:
        dotenv_path = join(dirname(__file__), '.env')
        load_dotenv(dotenv_path)
        self.exchange = ccxt.kraken( 
        { 'apiKey': os.getenv('KEY_KRAKEN'),
            'secret': os.getenv('SECRET_KRAKEN'),
            'enableRateLimit': True,
        }) 
        self.pair = pair

    def getBalance(self):
        return self.exchange.fetch_balance()

    def getOrders(self):
        return self.exchange.fetch_open_orders(self.pair)
    
    def getOrder(self, idOrder):
        return self.exchange.fetch_order(idOrder, self.pair)

    def cancelOrder(self, idOrder):
        return self.exchange.cancel_order(idOrder, self.pair)
    
    def editOrder(self, idOrder, price, volume):
        return self.exchange.edit_order(idOrder, self.pair, 'limit', 'buy', volume, price)
    
    def addOrder(self, typeOrder, price, volume):
        return self.exchange.create_order(self.pair, 'limit', typeOrder, volume, price)
