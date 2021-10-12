"""
This will update tickers list to remove top gainers and loosers top  (top 25) in original version
set this value withb this parameter TOP_GAINERS = 25
currently also hard coded to remove coins with greater that 8% gain last  24 hours or dropped below -2% in 24 hr period
these are lines where you can set the values according to you need
neg_coin = [ item['symbol'] for item in filter(lambda x: float(x['priceChangePercent'])<-2.0, change_per)]
pos_coin = [ item['symbol'] for item in filter(lambda x: float(x['priceChangePercent'])>=8.0, change_per)]

Also remove bottom 10 coins with respect to volume in 24 hours

these are removed because price change is very vaoltile and coins at top can fall down very easily, or coins at bottom could drop down even further.
this is suppsed to be used to trade lot of coins very fast so we dont a hold these risky coins.




"""
# used for directory handling
import glob
import sched, time
import re

import os
import numpy as np
from time import sleep
from datetime import datetime
import requests
from binance.client import Client

from helpers.parameters import parse_args, load_config
# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)


args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
EX_PAIRS = parsed_config['trading_options']['EX_PAIRS']
TICKERS_LIST = 'tickers_all_USDT.txt'

# Number of top coins to remove
TOP_GAINERS = 25
SIGNAL_BOT_NAME = "TOP_GAINERS"
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'
    YELLOW = '\033[33m'
    TURQUOISE = '\033[36m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    ITALICS = '\033[3m'

def create_ticker_list():
    url = f'http://edgesforledges.com/watchlists/download/binance/fiat/usdt/all'
    response = requests.get(url)

    with open(TICKERS_LIST, 'w') as f:
        for line in response.text.splitlines():
            if line.endswith(PAIR_WITH):
                currency = re.sub(r'BINANCE:(.*)' + PAIR_WITH, r'\1', line)
                if currency not in EX_PAIRS:
                    f.writelines(currency + '\n')
    print(f'{txcolors.SELL_PROFIT}>> Tickers CREATED from {url} tickers!!! {TICKERS_LIST} <<')
create_ticker_list()

def get_24hr_price(client_api):

    change_per = []
    tickers = [line.strip() for line in open(TICKERS_LIST)]
    prices = client.get_ticker()

    for coin in prices:
        
        for item in tickers:
            if item + PAIR_WITH == coin['symbol']:
               
                change_per.append(coin)

    sorted_change_per = [ item['symbol'] for item in sorted(change_per, key=lambda item: item['priceChangePercent'], reverse= True)]
    sorted_volume = [ item['symbol'] for item in sorted(change_per, key=lambda item: item['quoteVolume'], reverse= True)]
    neg_coin = [ item['symbol'] for item in filter(lambda x: float(x['priceChangePercent'])<-2.0, change_per)]
    pos_coin = [ item['symbol'] for item in filter(lambda x: float(x['priceChangePercent'])>=8.0, change_per)]
    #print(len(sorted_volume[-40 :]))
    return list(set(sorted_change_per[:TOP_GAINERS]+ sorted_change_per[-TOP_GAINERS :]+sorted_volume[-10 :] + pos_coin + neg_coin)), sorted_change_per        
    #sorted_change_per = sorted(change_per, key=lambda item: item['priceChangePercent'], reverse= True)
    #return sorted_change_per[:TOP_GAINERS]+ sorted_change_per[-TOP_GAINERS :]

#print (get_24hr_price(client))
top_coins, all_coins = get_24hr_price(client)
#print (top_coins)
if os.path.exists('top_gainers.txt'):
                    os.remove('top_gainers.txt')
if os.path.exists('tickers_wo_top_movers.txt'):
                    os.remove('tickers_wo_top_movers.txt')
tickers_wo_top_movers = list(set(all_coins)^set(top_coins))

for coin in top_coins:
    with open('top_gainers.txt', 'a+') as f:
        f.write(coin + '\n')

for coin in tickers_wo_top_movers:
    with open('tickers_wo_top_movers.txt', 'a+') as f:
        f.write(coin + '\n')

print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME} top gainers run complete')

def do_work():
    while True:
        top_coins = get_24hr_price(client)
        if os.path.exists('top_gainers.txt'):
                            os.remove('top_gainers.txt')
        try:

            top_coins, all_coins = get_24hr_price(client)
            #print (top_coins)
            if os.path.exists('top_gainers.txt'):
                                os.remove('top_gainers.txt')
            if os.path.exists('tickers_wo_top_movers.txt'):
                                os.remove('tickers_wo_top_movers.txt')
            tickers_wo_top_movers = list(set(all_coins)^set(top_coins))

            for coin in top_coins:
                with open('top_gainers.txt', 'a+') as f:
                    f.write(coin + '\n')

            for coin in tickers_wo_top_movers:
                with open('tickers_wo_top_movers.txt', 'a+') as f:
                    f.write(coin + '\n')


            print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME} top gainers run complete')
        except Exception as e:
            print(e)

        time.sleep(1*500)