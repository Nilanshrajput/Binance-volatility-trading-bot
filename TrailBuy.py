

# use if needed to pass args to external modules
import sys

# used for math functions
import math
from statistics import mean

# used to create threads & dynamic loading of modules
import threading
import multiprocessing
import importlib

# used for directory handling
import glob

import os
import numpy as np
from time import sleep
from datetime import datetime

from binance.client import Client
import glob
import time
import threading

from tradingview_ta import TA_Handler, Interval, Exchange
# used for dates
from datetime import date, datetime, timedelta

INTERVAL1MIN = Interval.INTERVAL_1_MINUTE # Main Timeframe for analysis on Oscillators and Moving Averages (15 mins)
INTERVAL5MIN = Interval.INTERVAL_5_MINUTES
INTERVAL1HR = Interval.INTERVAL_1_HOUR
INTERVAL4HR = Interval.INTERVAL_4_HOURS

from helpers.parameters import parse_args, load_config
# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)

SIGNAL_BOT_NAME = 'TrailBuy'

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

# Load trading vars
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
EX_PAIRS = parsed_config['trading_options']['EX_PAIRS']
TRADE_SLOTS = parsed_config['trading_options']['TRADE_SLOTS']

BUY_TRAIL_TIME = parsed_config['trading_options']['BUY_TRAIL_TIME']
TRAILING_BUY_PER = parsed_config['trading_options']['TRAILING_BUY_PER']
BUY_PER_INC = parsed_config['trading_options']['BUY_PER_INC']
NEG_COUNT = parsed_config['trading_options']['NEG_COUNT']
NEG_TIME_COUNT = parsed_config['trading_options']['NEG_TIME_COUNT']

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)

trail_list = []

# for colourful logging to the console
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

def get_sma(coin_data):
    EXCHANGE = 'BINANCE'
    SCREENER = 'CRYPTO'
        
    pair = coin_data['symbol']
    handler5MIN = TA_Handler(
        symbol=pair,
        exchange=EXCHANGE,
        screener=SCREENER,
        interval=INTERVAL5MIN,
        timeout= 5)
    handler1HR = TA_Handler(
        symbol=pair,
        exchange=EXCHANGE,
        screener=SCREENER,
        interval=INTERVAL1HR,
        timeout= 5)
    handler4HR = TA_Handler(
        symbol=pair,
        exchange=EXCHANGE,
        screener=SCREENER,
        interval=INTERVAL4HR,
        timeout= 5)
                        
    
    try:
        #analysis1MIN = handler5MIN.get_analysis()
        analysis5MIN = handler5MIN.get_analysis()
        analysis1HR = handler1HR.get_analysis()
        analysis4HR = handler4HR.get_analysis()
    except Exception as e:
        print(f'Exception: {e}')
        
        
    """ print(analysis1MIN.moving_averages)
    print(analysis4HR.moving_averages)
    print(analysis4HR.indicators['SMA50'])
    print(analysis4HR.indicators['SMA200'])
    print(analysis4HR.indicators['SMA5'])"""
    #print(analysis4HR.indicators)
    SMA5 = round(analysis5MIN.indicators['SMA5'],3)
    SMA50= round(analysis1HR.indicators['SMA50'],3)
    SMA200 = round(analysis4HR.indicators['SMA200'],3)
    with open('SMA_DATA.txt','a+') as f:
                    f.write(f"{pair} {coin_data['time']} \t {coin_data['price']} \t {SMA5} \t {SMA50} \t {SMA200} \t {analysis5MIN.moving_averages['RECOMMENDATION']} \t {analysis1HR.moving_averages['RECOMMENDATION']}\
                    \t {analysis4HR.moving_averages['RECOMMENDATION']} " + '\n')

    return {'SMA5':SMA5, 'SMA50':SMA50, 'SMA200':SMA200, 'analysis1HR':analysis1HR.moving_averages['RECOMMENDATION'] }
   
#get_sma('TRUUSDT')

# taken from external signals() from vol_scan
def get_buy_external_signals():
    global trail_list

    external_list = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.exs")
    for filename in signals:
        for line in open(filename):#[:TRADE_SLOTS+2]:
            symbol = line.strip()
            if symbol not in trail_list: 
                external_list[symbol] = symbol
                trail_list.append(symbol)
        try:
            os.remove(filename)
        except:
            pass

    #print(f"{trail_list} trail_list in trail ")
    #print(f"{external_list} external_siignales in trail ")

   
    return external_list



def get_price(client_api):
    global trail_list

    initial_price = {}
    tickers = trail_list #[line.strip() for line in open(TICKERS_LIST)]
    prices = client_api.get_all_tickers()

    for coin in prices:
        for item in tickers:
            #print(f"{coin['symbol']} coin['symbol'] in get price --------------------------------------" )
            if item == coin['symbol'] and all(item + PAIR_WITH  not in coin['symbol'] for item in EX_PAIRS):
                initial_price[coin['symbol']] = {'symbol': coin['symbol'],
                                                 'price': float(coin['price']),
                                                 'time': datetime.now(),
                                                 'price_list': [],
                                                 'change_price_list': [],
                                                 'updated_price': float(coin['price']),
                                                 'neg_count': 0.0,
                                                 'huge_drop': 0,
                                                 'pos_count':0.0,
                                                 'smv_10': 0.0,
                                                 'smv_10': 0.0,
                                                 'smv_10': 0.0,
                                                 }
    #print(f"{trail_list} trail_list in get price ")
    return initial_price


def do_work():
    global trail_list 

    _=  get_buy_external_signals()
    # Initializing coins for data storage.
    init_price = get_price(client)
    #print(f"{init_price} init_price############################################### ")

    while True:

        #sleep(BUY_TRAIL_TIME)
        try:
            sleep(BUY_TRAIL_TIME)
            new_signaled_coins =  get_buy_external_signals()
            

            # Requesting the latest coin prices
            last_price = get_price(client)
            #print(f"{last_price} last_price%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% ")
            #print(f"{trail_list} ----------------------------------------------------------------------------")

            for new_signaled_coin in new_signaled_coins:
                init_price[new_signaled_coin] = last_price[new_signaled_coin]
                
            if os.path.exists('signals/trail_buy.exs'):
                        os.remove('signals/trail_buy.exs')

            for coin in last_price:

                init_price[coin]['price_list'].append(float(last_price[coin]['price']))

                per_change = 100*(last_price[coin]['price']-init_price[coin]['updated_price'])/init_price[coin]['updated_price']
                
                init_price[coin]['change_price_list'].append(per_change)
                print (f' price changed by {per_change}% for {coin}+++++++++++++++++++++++++++++++++++++++++++')
                timediff = init_price[coin]['time']- last_price[coin]['time']
                timediff = timediff.total_seconds()
                if per_change < TRAILING_BUY_PER:
                    init_price[coin]['updated_price'] = last_price[coin]['price']
                    print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME} :{coin} Price dropped below TRAILING_BUY_PER waiting {BUY_TRAIL_TIME} sec more befor next check')
                    init_price[coin]['neg_count'] = init_price[coin]['neg_count'] +1
                    if per_change <= 1.5*TRAILING_BUY_PER:
                        init_price[coin]['huge_drop'] = 1
                        init_price[coin]['neg_count'] = init_price[coin]['neg_count'] +1
                    else :
                        init_price[coin]['huge_drop'] = 0
                    if per_change <= 2*TRAILING_BUY_PER:
                        init_price[coin]['huge_drop'] = 1
                        init_price[coin]['neg_count'] = init_price[coin]['neg_count'] +1
                    if per_change <= 3*TRAILING_BUY_PER:
                        init_price[coin]['huge_drop'] = 1
                        init_price[coin]['neg_count'] = init_price[coin]['neg_count'] +1
                    
                    if per_change <= 5*TRAILING_BUY_PER:
                        init_price[coin]['huge_drop'] = 1
                        init_price[coin]['neg_count'] = init_price[coin]['neg_count'] +3
                    
                   

                if  0.7*init_price[coin]['price']<last_price[coin]['price']< 0.9985*init_price[coin]['price'] and init_price[coin]['neg_count']>=NEG_COUNT and  init_price[coin]['huge_drop']==0 and 0.1 <= per_change <=0.2 or init_price[coin]['pos_count']>2:# or (timediff>=NEG_TIME_COUNT*BUY_TRAIL_TIME) sum(init_price[coin]['change_price_list'])<-.15 :#or mean(init_price[coin]['change_price_list'])<0.05: # per_change > BUY_PER_INC and per_change<0.3:
                    
                    
                    sma  = get_sma(last_price[coin])
                    if last_price[coin]['price']> 1.002*sma['SMA200'] and sma['analysis1HR']=='STRONG_BUY':
                    
                        print(f'{txcolors.TURQUOISE}{SIGNAL_BOT_NAME}: detected a TRAIL Buy signal on{txcolors.END} '
                                f'{txcolors.TURQUOISE}{coin}{txcolors.END}'
                                )
                        with open('signals/trail_buy.exs', 'a+') as f:
                            f.write(init_price[coin]["symbol"] + '\n')

                        with open('trail_buy_signal_history/signal_trail.txt', 'a+') as f:
                            signal_trail = str(init_price[coin]["symbol"]) + '\t' + str(init_price[coin]['updated_price']) + '\t' + str(init_price[coin]['price']) + '\t'  + str(init_price[coin]['time']) + '\t'  + \
                                str(last_price[coin]['time']) + '\t' + str(last_price[coin]['price'])  + '\t' + str(init_price[coin]['change_price_list']) + '\t' + str(init_price[coin]['price_list']) + '\n'
                            f.write(signal_trail)

                        trail_list.remove(coin)
                        init_price.pop(coin)
                        last_price.pop(coin)
                    else : 
                        trail_list.remove(coin)
                        init_price.pop(coin)
                        last_price.pop(coin)
                    
                
                if last_price[coin]['price']< 0.7*init_price[coin]['price'] and init_price[coin]['neg_count']>=NEG_COUNT+4:
                    
                    sma  = get_sma(last_price[coin])
                    if last_price[coin]['price']> 1.002*sma['SMA200'] and sma['analysis1HR']=='STRONG_BUY':
                    
                        print(f'{txcolors.TURQUOISE}{SIGNAL_BOT_NAME}: detected a TRAIL Buy signal on{txcolors.END} '
                                f'{txcolors.TURQUOISE}{coin}{txcolors.END}'
                                )
                        with open('signals/trail_buy.exs', 'a+') as f:
                            f.write(init_price[coin]["symbol"] + '\n')

                        with open('trail_buy_signal_history/signal_trail.txt', 'a+') as f:
                            signal_trail = str(init_price[coin]["symbol"]) + '\t' + str(init_price[coin]['updated_price']) + '\t' + str(init_price[coin]['price']) + '\t'  + str(init_price[coin]['time']) + '\t'  + \
                                str(last_price[coin]['time']) + '\t' + str(last_price[coin]['price'])  + '\t' + str(init_price[coin]['change_price_list']) + '\t' + str(init_price[coin]['price_list']) + '\n'
                            f.write(signal_trail)

                        trail_list.remove(coin)
                        init_price.pop(coin)
                        last_price.pop(coin)
                    else : 
                        trail_list.remove(coin)
                        init_price.pop(coin)
                        last_price.pop(coin)
                    
                 
                        
                elif last_price[coin]['price']>1.1*init_price[coin]['price']:
                    trail_list.remove(coin)
                    init_price.pop(coin)
                    last_price.pop(coin)

                if per_change > TRAILING_BUY_PER and per_change <0 and init_price[coin]['neg_count']>=NEG_COUNT/2 :
                    init_price[coin]['updated_price'] = last_price[coin]['price']
                    print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME} :{coin} Price dropped below TRAILING_BUY_PER waiting {BUY_TRAIL_TIME} sec more befor next check')
                    init_price[coin]['neg_count'] = init_price[coin]['neg_count'] +1
                
                if  per_change>0.1 and  init_price[coin]['neg_count']>=NEG_COUNT:
                    init_price[coin]['pos_count'] +=1

                if per_change >0.3:
                    trail_list.remove(coin)
                    init_price.pop(coin)
                    last_price.pop(coin)
                
                if last_price[coin]['price']<1.001*init_price[coin]['price']:
                    init_price[coin]['updated_price'] = last_price[coin]['price']





                """elif per_change < 0:
                    init_price[coin]['updated_price'] = last_price[coin]['price']
                   """       
        except Exception as e:
            print(e)
