import time
from dotenv import load_dotenv
import websocket
import json
import threading
import sys
import resources as rs
import exchange as ex
import pandas as pd
from decimal import Decimal
import os
from os.path import join, dirname
import ccxt

## Class that will handle the websocket connection and look for price walls to positionate before them
class AutoJumper:
    def __init__(self, pair1, pair2, price, topPrice, volume):
        dotenv_path = join(dirname(__file__), '.env') ## Path to .env file
        load_dotenv(dotenv_path)
        self.pair1 = pair1.upper()
        self.pair2 = pair2.upper()
        self.pair = self.pair1 + '/' + self.pair2
        self.price = float(price)
        self.topPricePercentage = float(topPrice) ## Percentage of the first bid price
        self.topPrice = 0 ## Max price that self.price can be
        self.volume = float(volume)
        self.orderId = ''
        self.api_book = {'bid':{}, 'ask':{}}
        self.api_depth = 100
        self.exchange = ex.Exchange(self.pair)
        self.state = 1 ## 1 = Bot on | 0 = Bot off

    ## Helper methods

    ## Return float of data
    def dicttofloat(self, data):
        return float(data[0])

    ## Return dataframe of instances.csv
    @staticmethod
    def getInstancesFromCSV():
        columns = ['pair1', 'pair2', 'price', 'topPrice', 'volume', 'status']
        df = pd.read_csv('instances.csv', names=columns)
        return df

    ## Return dataframe of edit_pair_instances.csv
    def getEditedBotFromCSV(self):
        columns = ['pair1', 'pair2', 'price', 'topPrice', 'volume']
        df = pd.read_csv(f'edit_{self.pair1}_{self.pair2}.csv', names=columns)
        return df

    ## Check if self.pair instance is on
    def checkInstanceOn(self):
        instances = self.getInstancesFromCSV()
        if len(instances) == 0:
            return False
        else:
            for i in range(len(instances)):
                if instances['pair1'][i] == self.pair1 and instances['pair2'][i] == self.pair2:
                    return True
            return False


    def saveInstanceToCSV(self, instance):
        columns = ['pair1', 'pair2', 'price', 'topPrice', 'volume', 'status']
        instances = self.getInstancesFromCSV()
        try:
            if instances.empty:
                df = pd.DataFrame(instance, columns=columns, index=[0])
                df.to_csv('instances.csv', index=False, header=False)
            else:
                df = pd.DataFrame(instance, columns=columns, index=[0])
                data = [instances, df]
                dfs = pd.concat(data, ignore_index=True)
                dfs.to_csv('instances.csv', index=False, header=False)
            return True
        except Exception as e:
            print(e)
            return False

    ## Update self.api_book with data from websocket
    def api_book_update(self, api_book_side, api_book_data):
        for data in api_book_data:
            price_level = data[0]
            volume = data[1]
            if float(volume) > 0.0:
                self.api_book[api_book_side][price_level] = volume
            else:
                self.api_book[api_book_side].pop(price_level)
            if api_book_side == 'bid':
                self.api_book['bid'] = dict(sorted(self.api_book['bid'].items(), key=self.dicttofloat, reverse=True)[:self.api_depth])
            elif api_book_side == 'ask':
                self.api_book['ask'] = dict(sorted(self.api_book['ask'].items(), key=self.dicttofloat)[:self.api_depth])

    ## Check if price is < that the first ask price
    def checkValidBidPrice(self, price, orderbook):
        asks = sorted(orderbook['ask'].items(), key=self.dicttofloat)

        if float(asks[0][0]) > price:
            return True
        else:
            return False   

    def checkIfOrderOpen(self):
        orders = self.exchange.getOrders()
        for order in orders:
            if order['pair'] == self.pair and order['type'] == 'buy' and order['status'] == 'open':
                i += 1
                if i == 1:
                    self.orderId = order['id']
                    print('Orden encontrada')
                    rs.sendTelegramMessage(f"Bot {self.pair}: Orden encontrada.")                        
                return True
        return False 
    
    def checkTopPrice(self, percentage, orderbook):
        bids = sorted(orderbook['bid'].items(), key=self.dicttofloat, reverse=True)
        percentage = float(percentage) / 100
        topPrice = float(bids[0][0]) - (float(bids[0][0]) * float(percentage))
        return topPrice

    def checkOrderBookWall(self, ownOrderVolume, ownOrderPrice, orderbook):
        bids = sorted(orderbook['bid'].items(), key=self.dicttofloat, reverse=True)
        sumBids = 0

        for bid in bids:
            price = float(bid[0])
            volume = float(bid[1])
            sumBids += volume
            if sumBids > ownOrderVolume * 0.5 and price > ownOrderPrice:
                if volume > 0.4 * ownOrderVolume:
                    return True, volume, price
        return False, 0, 0

    def checkEditedBot(self):
        if os.path.exists(f'edit_{self.pair1}_{self.pair2}.csv'):
            return True
        else:
            return False

    def newOrderPrice(self, price):
        n_decimals = rs.n_Decimals(price)
        priceToAdd = rs.createDecimalNumber(n_decimals)
        newPrice = Decimal(str(price)) + Decimal(str(priceToAdd))
        return float(newPrice)

    def autoDelete(self):
        self.state = 0
        instances = self.getInstancesFromCSV() 

        for i in range(len(instances)):
            if instances['pair1'][i] == self.pair1 and instances['pair2'][i] == self.pair2:
                instances = instances.drop([i])
        
        instances.to_csv('instances.csv', index=False, header=False)
        rs.sendTelegramMessage(f"Bot {self.pair} apagandose...")
        try:
            self.exchange.cancelOrder(self.orderId)
        except ccxt.BaseError as e:
            print(e)
                   
    def ws_thread(self):
        # WebSocket thread
        ws = websocket.WebSocketApp('wss://ws.kraken.com/', on_open=self.ws_open, on_message=self.ws_message , on_error=self.ws_error)
        ws.run_forever(ping_interval=30, reconnect=5)   
        rs.sendTelegramMessage(f"Bot {self.pair} apagado.")
        self.state = 0
   
    def ws_error(self, ws, error):
        print('WebSocket error')
        print(error)
        
    def ws_open(self, ws):
        try:
            ws.send('{"event":"subscribe", "subscription":{"name":"book", "depth":%(api_depth)d}, "pair":["%(api_symbol)s"]}' %{'api_depth':self.api_depth, 'api_symbol':self.pair})
        except Exception as e:
            print(e)
            sys.exit()

    def ws_message(self, ws, ws_data):
        if self.state == 0:
            ws.close()      
        api_data = json.loads(ws_data)
        if 'event' in api_data:
            return
        else:
            if 'as' in api_data[1]:
                self.api_book_update('ask', api_data[1]['as'])
                self.api_book_update('bid', api_data[1]['bs'])
            else:
                for data in api_data[1:len(api_data)-2]:
                    if 'a' in data:
                        self.api_book_update('ask', data['a'])
                    elif 'b' in data:
                        self.api_book_update('bid', data['b'])
    def mainThread(self):
        try:
            if self.checkIfOrderOpen(): ## Ckeck if pair order is open and get order id
                    if self.checkValidBidPrice(self.price, self.api_book): ## Check if inicialized price is valid
                        editedOrder = self.exchange.editOrder(self.orderId, self.price, self.volume)
                        self.orderId = editedOrder['id']
                        rs.sendTelegramMessage(f"Bot {self.pair}: Orden editada.")
                    else:
                        rs.sendTelegramMessage(f"Bot {self.pair}: Error editando orden.\nError: Precio mayor que la 1ª posicion ask.")
                        self.autoDelete()

            else:
                if self.checkValidBidPrice(self.price, self.api_book):
                    newOrder = self.exchange.addOrder('buy', self.price, self.volume)
                    self.orderId = newOrder['id']
                    rs.sendTelegramMessage(f"Bot {self.pair}: Orden añadida.")
                    print(newOrder)
                else:
                    rs.sendTelegramMessage(f"Bot {self.pair}: Error añadiendo orden.\nError: Precio mayor que el 1º bid.")
                    self.autoDelete()

            while self.state == 1: 
                waitTime = 0
                time.sleep(1)
                if not self.checkInstanceOn():
                    self.autoDelete()
                
                ## Check if bot has been edited from telegram
                if self.checkEditedBot():
                    editedBot = self.getEditedBotFromCSV()
                    editedBotPrice = editedBot['price'][0]
                    editedBotVolume = editedBot['volume'][0]
                    editedBotTopPrice = editedBot['topPrice'][0]

                    if not editedBotPrice == 'None':
                        self.price = float(editedBotPrice)
                    if not editedBotVolume == 'None':
                        self.volume = float(editedBotVolume)
                    if not editedBotTopPrice == 'None':
                        self.topPricePercentage = float(editedBotTopPrice)

                    orderEdited = self.exchange.editOrder(self.orderId, self.price, self.volume)
                    self.orderId = orderEdited['id']
                    os.remove(f'edit_{self.pair1}_{self.pair2}.csv')
                    rs.sendTelegramMessage(f"Bot {self.pair} editado")

                ## Check what is the highest price that the bot can reach to meet the minimum percentage
                topPrice = self.checkTopPrice(self.topPricePercentage, self.api_book)

                ## Check if exist a wall in the order book
                checkWall, wallVolume, wallPrice = self.checkOrderBookWall(self.volume, self.price, self.api_book)

                ## If the wallPrice is greater than the maximum price that the bot can reach, check if topPrice can be edited
                if wallPrice > topPrice:
                    validPrice = topPrice
                    ## 1% tolerance to avoid abuse of the price edition
                    ## If the topPrice is greater than the current price with tolerance, it is edited
                    if self.price > (validPrice + validPrice * 0.01) or self.price < (validPrice - validPrice * 0.01):
                        orderEdited = self.exchange.editOrder(self.orderId, validPrice, self.volume)
                        waitTime += 5
                        self.price = validPrice
                        self.orderId = orderEdited['id']
                        print(f'Order edited at top price {topPrice} successfully')
                        rs.sendTelegramMessage(f"Bot {self.pair} editado al %pabilo mínimo.\nPrecio {self.price}")

                ## The wallPrice is in our action range
                else:
                    validPrice = wallPrice
                    if checkWall:
                        newPrice = self.newOrderPrice(validPrice)
                        if newPrice != self.price and newPrice <= topPrice:
                            editedOrder = self.exchange.editOrder(self.orderId, newPrice, self.volume)
                            self.price = newPrice
                            waitTime += 5
                            print(f'Wall vol: {wallVolume}{self.pair1} - price: {wallPrice}{self.pair2} jumped.\nBot new price: {self.price}')
                            rs.sendTelegramMessage(f'Wall en vol: {wallVolume}{self.pair1} - price: {wallPrice}{self.pair2}.\nBot new price: {self.price}')
                            self.orderId = editedOrder['id']

                time.sleep(waitTime)   ## Prevent the bot from editing orders so fast that it doesn't catch wicks

        except ccxt.InsufficientFunds as e:
            print('Fondos insuficientes: ' + str(e))
            rs.sendTelegramMessage(f"Bot {self.pair} error: Fondos insuficientes.\nVuelve a iniciar el bot.")
            self.autoDelete()
        except ccxt.InvalidOrder as e:
            print('Orden invalida: ' + str(e))
            rs.sendTelegramMessage(f"Bot {self.pair} error: Orden invalida.\nVuelve a iniciar el bot.")
            self.autoDelete()
        except ccxt.NetworkError as e:
            print('Error de red: ' + str(e))
            rs.sendTelegramMessage(f"Bot {self.pair} error: Error de red.\nVuelve a iniciar el bot.")
            self.autoDelete()
        except Exception as e:
            rs.sendTelegramMessage(f"Bot {self.pair} error: {str(e)}")
            self.autoDelete()
        
    def start(self):
        print(f'Starting bot {self.pair}...')
        t1 = threading.Thread(target=self.mainThread, name='t1')
        t2 = threading.Thread(target=self.ws_thread, name='t2')

        # Start new thread for WebSocket interface
        t1.start()
        # Start new thread for main thread autoJumper
        t2.start()




