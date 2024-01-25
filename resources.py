import requests
from dotenv import load_dotenv
import os
from os.path import join, dirname

def createDecimalNumber(n_decimales):
    return 10 ** -n_decimales

def n_Decimals(price):
    return len(str(price).split('.')[1])

def sendTelegramMessage(message):
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    load_dotenv()
    token = os.getenv('TELEGRAM_TOKEN')
    group_id = os.getenv('TELEGRAM_GROUP_ID')
    requests.post(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={group_id}&text={message}')
