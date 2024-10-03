from flask import Flask, request
from flask_cors import CORS

from configparser import ConfigParser
from discordbot.discord import DiscordBot
from robinhood.robinhood import RobinhoodClient
from telegrambot.telegrambot import TelegramBot
import pyotp
import json
from threading import Thread
import numpy as np
import pytz

import time
from datetime import datetime
import os

config = ConfigParser()
file_path ="config.ini"
config.read(file_path)

with open('settings/setting.json', 'r') as json_file:
    saved_datas = json.load(json_file)

class MyBot:
    def __init__(self):
        # super().__init__()
        self.is_alive =False
        self.pause_threading_event = False
        self.connect_check()
         
    def connect_check(self):
        #TELEGRAM CONNECT
        try:
            self.telegramBot = TelegramBot(saved_datas["TELEGRAM_TOKEN"], saved_datas["TELEGRAM_CHAT_ID"])
            print(f'Telegram connect success')
        except Exception as e :
            print(f'Telegram connect error: {e}')
            
        #ROBINHOOD CONNECT
        i=0
        self.robinhood = []
        for account in saved_datas['accounts']:
            try:
                mfa= pyotp.TOTP(account['totp_secret']).now()
                robin = RobinhoodClient(account['username'], account['password'], mfa, account['type'], account['account_number'])
                
                isconnect = robin.check_connect()
                if isconnect == False:
                    self.telegramBot.send_message(f"Robinhood connect error: {account['username']} {account['type']}")    
                    print(f'Robinhood connect error')
                else :
                    robin.account_type = account['type']
                    robin.account_number=account['account_number']
                    robin.is_connect = True
                    print(f'Robinhood account{i} connect success')
                self.robinhood.append(robin)
            except Exception as e:
                self.telegramBot.send_message(f"Robinhood connect error: {account['username']} {account['type']}")
                print(f'Robinhood connect error: {e}')
            i = i+1
        #DISCORD CONNECT
        try: 
            channels = []
            channel_ids = []
            tokens = []
            # Extract values from the parsed data
            for discord in saved_datas['discords']:
                channels.append(discord['channel'])
                channel_ids.append(discord['channel_id'])
                tokens.append(discord['token'])
            self.discordBot = DiscordBot(channels, channel_ids, tokens)
            for channel, channel_id, token in zip(channels,channel_ids,tokens):
                is_connection = self.discordBot.check_connection(channel_id, token)
                if is_connection == False:
                    self.telegramBot.send_message(f"DISCORD channel {channel.upper()} connect error")
                    print(f'Discord {channel} connect error')
                else :
                    print(f'Discord {channel} connect success')
        except Exception as e:
            self.telegramBot.send_message(f"DISCORD connect error:")
            print(f'Discord connect error: {e}')
            
    def on_sellall(self):
        for i in range(0,7):
            print(self.robinhood[i].is_connect)
            if self.robinhood[i].is_connect ==False:
                continue
            self.robinhood[i].sell_all()

    def on_start(self):
        if self.is_alive: 
            print("Trading bot is running. You can't create new bot.")
            return
        self.is_alive = True
        thread = Thread(self.run_bot())
        thread.start()
        # self.run_bot()
 
    def run_bot(self):
        now = datetime.now()
        tz_CentralTime = pytz.timezone('US/Central')
        try:
            start_time = config["TIMESETTING"]["market_hours_start"]
            end_time = config["TIMESETTING"]["market_hours_end"]
        except Exception as e:
            print(e)
            return
        datetime_central = datetime.now(tz_CentralTime)
        while self.is_alive == True:
            current_time = datetime_central.strftime("%H:%M:%S")
            market_open = datetime_central.replace(hour = int(start_time.split(":")[0],base=10), minute =int(start_time.split(":")[1], base=10), second = int(start_time.split(":")[2], base=10), microsecond= 0)
            market_close = datetime_central.replace(hour = int(end_time.split(":")[0],base=10), minute =int(end_time.split(":")[1], base=10), second = int(end_time.split(":")[2], base=10), microsecond= 0)
            if datetime_central >= market_open and datetime_central <= market_close:
                if self.pause_threading_event==False: 
                    index = -1
                    # print(f'current_time: {datetime_central} market_open: {market_open} market_close: {market_close}')
                    for channel, channel_id, token in zip(self.discordBot.channels, self.discordBot.channel_ids, self.discordBot.authorization):
                        index = index + 1
                        print(index)
                        signals = self.discordBot.getSignal_fromDiscord(channel, channel_id, token) 
                        if signals == None:
                            self.telegramBot.send_message(f"Discord Channel {channel.upper()} is not connected.")
                            continue
                        for signal in signals:
                            for i in range(0,7):
                                if self.robinhood[i].is_connect == False : 
                                    print(f"robinhood account {i} is not connected.")
                                    continue
                                if saved_datas['discord_channel_use'][i][index] != 1:
                                    print(f"{channel} excluses in Robinhood account{index}")
                                    continue
                                ticker_ex_list=saved_datas["ticker_exclusion_list"][i]
                                if signal['ticker'] in ticker_ex_list: continue
                                print(f"{i} => ", self.place_order(signal, channel,i, index))
                            self.confirm_discordsignal(channel, signal['timestamp'])  
                        
            time.sleep(10)

    def confirm_discordsignal(self,channel, timestamp):
        if not os.path.exists(self.discordBot.last_time_save_file):
            inital_last_time_str = '1900-01-01T00:00:00.000000+00:00'
            data = {
                "et": inital_last_time_str,
                "dt": inital_last_time_str,
                "mm": inital_last_time_str,
                "sre_qa": inital_last_time_str,
                "sre_pa": inital_last_time_str
            }
            try:
                with open(self.discordBot.last_time_save_file, "w") as file:
                    json.dump(data, file, indent =4)
            except Exception as e:
                return
        else :
            with open(self.discordBot.last_time_save_file,"r") as file:
                data= json.load(file)
            data[channel] = timestamp
            try:
                with open(self.discordBot.last_time_save_file, "w") as file:
                    json.dump(data, file, indent =4)
            except Exception as e:
                return
            return
    def place_order(self, signal, channel, account_index, channel_index) :
        print(f'---------------------------------\n signal => {signal} \n ----------------------\n')
        ticker = signal['ticker']
        strike_price = signal['strike_price']
        price = signal['price']
        trade_type = signal['trade_type']
        desirable_expiration_date = signal['expiration_date']
        selected_expiration = self.robinhood[account_index].select_expiration_date(ticker, desirable_expiration_date)
        option_id = self.robinhood[account_index].get_option_id(
            ticker,
            strike_price,
            trade_type,
            selected_expiration
        )
        if option_id == None: return False
        if len(option_id)==0 : return False
        # print(f"EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE\n{option_id[0]}  {len(option_id)}\nEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
        # return
        bid_price, ask_price = self.robinhood[account_index].get_bid_ask_price(option_id[0])
        midpoint_price = (bid_price + ask_price)/2.0
        threshold = float(saved_datas["threshold"][account_index])
        delay = float(saved_datas["delay"][account_index])
        multify = (1+threshold/100)

        print(f"{ticker} {strike_price} {trade_type} {selected_expiration} => {option_id[0]} {bid_price} {ask_price} ")
        if(ask_price > float(price)*multify) :
            self.telegramBot.send_message(f"{channel.upper()} {ticker} {strike_price} initial buy-in price too high.")
            return False
        channel_caps= saved_datas['cap_discord_channel'][account_index]
        cap = channel_caps[channel_index]
        max_contracts = int(float(cap) // (midpoint_price * 100))

        # Place the buy order
        order = self.robinhood[account_index].order_buy_limit(ticker,
                                        selected_expiration, 
                                        strike_price, 
                                        trade_type, 
                                        quantity=max_contracts, 
                                        limitPrice=midpoint_price)
        if order=="PDT" :
            print(f"{channel.upper()} {ticker} {strike_price} PDT warning")
            self.telegramBot.send_message(f"{channel.upper()} {ticker} {strike_price} PDT warning")
            return False
        elif order == "invalid_parameter":
            print(f"{channel.upper()} {ticker} {strike_price} invalid elements in buy signal")
            self.telegramBot.send_message(f"{channel.upper()} {ticker} {strike_price} invalid elements in buy signal")
            return False
        elif order =="not_enough" :
            print(f"{channel.upper()} {ticker} {strike_price} insufficient balance")
            self.telegramBot.send_message(f"{channel.upper()} {ticker} {strike_price} insufficient balance")
            return False
        elif order == "Warning" :
            print(f"{channel.upper()} {ticker} {strike_price} connection error")
            self.telegramBot.send_message(f"{channel.upper()} {ticker} {strike_price} connection error")
            return False

        # print(f"-@@@@@@@@@@@@@@@@@@@\n{order}\n -@@@@@@@@@@@@@@@@@@@@@@@--")
        start_time = time.time()

        while time.time() - start_time < 30:
            _ , current_ask_price = self.robinhood[account_index].get_bid_ask_price(option_id[0])

            if current_ask_price >= multify * float(price):
                self.robinhood[account_index].cancel_order(int(order))
                self.telegramBot.send_message(f"{channel} {ticker} {strike_price} buy-in price increased too quickly.")
                return True
            
            # Check if the order is filled
            order_info = self.robinhood[account_index].get_order_info(int(order))
            if order_info != None and order_info['state'] == 'filled':
                return True
            time.sleep(1)
        # Cancel the order if not filled within 30 seconds
        self.robinhood[account_index].cancel_order(int(order))
        self.telegramBot.send_message(f"{channel} {ticker} {strike_price} buy order not filled in time.")
    

mybot = MyBot()
     
# Create a Flask application instance
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Define a route for the root URL
@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/run')
def bot_run() :
    mybot.on_start()
    return "Hi"

@app.route('/resume')
def resume() :
    mybot.pause_threading_event=False
    return "Hi"

@app.route('/pause')
def pause() :
    mybot.pause_threading_event=True
    return "Hi"

@app.route('/save_settings',methods=['POST'])
def save_settings():

    param1 = request.args.get('data')
    if request.is_json:
        # Get the JSON data
        data = request.get_json()
        print('Received JSON data:', data) 
    with open("settings/setting.json","w") as file:
        json.dump(data, file)
    # print(file_data)
    return "HI"
 
@app.route('/sell_all')
def sell_all():
    mybot.on_sellall()
    return "Sell_all"

@app.route('/get_settings')
def get_settings():
    with open("settings/setting.json", "r") as file:
        datas= json.load(file)
    print(datas)
    return datas
# Run the server
if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=8080)
