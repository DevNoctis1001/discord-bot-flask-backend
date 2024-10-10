from flask import Flask, request
from flask_cors import CORS

from configparser import ConfigParser
from discordbot.discord import DiscordBot
from robinhood.robinhood import RobinhoodClient
from telegrambot.telegrambot import TelegramBot
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


class MyBot:
    def __init__(self):
        # Bot active state
        self.is_alive =False
        # Robinhood account active state
        self.account_use=[1, 1, 1, 1, 1, 1, 1]
        # All connection state check
        self.connect_check()
         
    # All connection state check
    def connect_check(self):
        
        with open('settings/setting.json', 'r') as json_file:
            saved_datas = json.load(json_file)

        #TELEGRAM CONNECT    
        try:
            self.telegramBot = TelegramBot(saved_datas["TELEGRAM_TOKEN"], saved_datas["TELEGRAM_CHAT_ID"])
        except Exception as e :
            print(f'Telegram connect error: {e}')
            
        #ROBINHOOD CONNECT
        i=0
        self.robinhood = []
        for account in saved_datas['accounts']:
            try:
                robin = RobinhoodClient(account['username'], account['password'], account['totp_secret'], account['type'], account['account_number'])
                isconnect = robin.check_connect()
                if isconnect == False:
                    self.telegramBot.send_message(f"🔥Robinhood account is not connected.\n\nAccount Number:{account['account_number']}")    
                    print(f'Robinhood connect error')
                else :
                    robin.account_type = account['type']
                    robin.account_number=account['account_number']
                    robin.is_connect = True
                    
                    print(f'Robinhood account{i} connect success')
                self.robinhood.append(robin)
            except Exception as e:
                self.telegramBot.send_message(f"🔥Robinhood account is not connected.\n\nAccount Number:{account['account_number']}")    
                print(f'Robinhood connect error: {e}')
            i = i + 1

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
                    self.telegramBot.send_message(f"🔥Discord Channel is not connected.\n\nChannel Name: {channel.upper()}")
                    print(f'Discord {channel} connect error')
                else :
                    print(f'Discord {channel} connect success')
        except Exception as e:
            print(f'Discord connect error: {e}')
            
    # Sell all the active position for the specific robinhood account. (index is -1: for all account  else: for the index account)
    def on_sellall(self, index):
        if index == -1:
            for i in range(0,7):
                if self.robinhood[i].is_connect ==False:
                    self.telegramBot.send_message(f"🔥Robinhood account is not connected.\n\nAccount Number:{self.robinhood[i].account_number}")    
                    continue
                self.robinhood[i].sell_all()
        else :
            if self.robinhood[index].is_connect == True:
                self.robinhood[index].sell_all()

    # Active the specific robinhood account. (index is -1: for all account  else: for the index account)
    def resume(self, index):
        if index==-1 : 
            for i in range(0,7) :
                self.account_use[index] = 1
        else :
            self.account_use[index] = 1
    
    # Pause the specific robinhood account. (index is -1: for all account  else: for the index account)
    def pause(self, index):

        if index==-1 : 
            for i in range(0,7) :
                self.account_use[index] = 0
        else :
            self.account_use[index] = 0

    # Start the bot.
    def on_start(self):
        if self.is_alive:   # If the bot is in active : return
            print("Trading bot is running. You can't create new bot.")
            return
        
        self.is_alive = True
        thread = Thread(target=self.run_bot)  # Create new thread
        thread.start()

    # Execute the bot.
    def run_bot(self):
        # US/Central timezone
        tz_CentralTime = pytz.timezone('US/Central')  

        # Import the start_time and end_time from config file.
        try:
            start_time = config["TIMESETTING"]["market_hours_start"]
            end_time = config["TIMESETTING"]["market_hours_end"]
        except Exception as e:
            return

        # Change the now time to US/Central timezone time.

        while self.is_alive == True:  # Run when the bot is actived.
            # Import the setting datas.
            with open('settings/setting.json', 'r') as json_file:
                saved_datas = json.load(json_file)

            datetime_central = datetime.now(tz_CentralTime)
            current_time = datetime_central.strftime("%H:%M:%S")
            market_open = datetime_central.replace(hour = int(start_time.split(":")[0],base=10), minute =int(start_time.split(":")[1], base=10), second = int(start_time.split(":")[2], base=10), microsecond= 0)
            market_close = datetime_central.replace(hour = int(end_time.split(":")[0],base=10), minute =int(end_time.split(":")[1], base=10), second = int(end_time.split(":")[2], base=10), microsecond= 0)
            
            if datetime_central >= market_open and datetime_central <= market_close:   # Now is in market time.
                index = -1
                # Iterate
                for channel, channel_id, token in zip(self.discordBot.channels, self.discordBot.channel_ids, self.discordBot.authorization):
                    index = index + 1
                    # Fetch the signals from the specific discord channel.
                    signals = self.discordBot.getSignal_fromDiscord(channel, channel_id, token) 
                    print(f'Signal of {channel.upper()} => {signals}')
                    # If signals is None (thus connect error): skip
                    if signals == None:  
                        self.telegramBot.send_message(f"🔥Discord Channel is not connected.\n\nChannel Name: {channel.upper()}")
                        continue
                    # Iterate every signal
                    for signal in signals:
                        for i in range(0,7):  # Iterate every robinhood accounts.
                            # If robinhood account is non-active : skip
                            if self.account_use[i] == False:
                                print(f"robinhood account{i} is paused.")
                                continue
                            
                            # If robinhood account isn't connected: skip
                            if self.robinhood[i].is_connect == False : 
                                print(f"robinhood account {i} is not connected.")
                                continue
                            
                            # If robinhood account excluse this channel: skip
                            if saved_datas['discord_channel_use'][i][index] != 1:
                                print(f"{channel} excluses in Robinhood account{i}")
                                continue

                            # If ticker from the signal is in exclusion list: skip
                            ticker_ex_list=saved_datas["ticker_exclusion_list"][i]
                            if signal['ticker'] in ticker_ex_list: continue

                            #If ticker from the signal is opened already : skip
                            if signal['ticker'] in self.robinhood[i].orders: continue
                            # Place order and print the result
                            print(f"{i} => ", self.place_order(signal, channel,i, index))
                        
                        # If the signal passes through all accounts: record the timestamp so that it is not used afterwards.
                        self.confirm_discordsignal(channel, signal['timestamp'])  

            else :
                print(current_time," ", market_open," ", market_close)
                print("This is not market time.")

            # Iterate every 1 min.
            time.sleep(60)

    # Record the timestamp so that it is not used afterwards.
    def confirm_discordsignal(self,channel, timestamp):
        if not os.path.exists(self.discordBot.last_time_save_file):  # If the save file don't exist: 
            inital_last_time_str = '1900-01-01T00:00:00.000000+00:00'
            data = {
                "et": inital_last_time_str,
                "dt": inital_last_time_str,
                "mm": inital_last_time_str,
                "sre_qt": inital_last_time_str,
                "sre_pa": inital_last_time_str
            }
            try:
                with open(self.discordBot.last_time_save_file, "w") as file:
                    json.dump(data, file, indent =4)
            except Exception as e:
                return
        else :  # If the save file exists already: 
            with open(self.discordBot.last_time_save_file,"r") as file:
                data= json.load(file)
            data[channel] = timestamp
            try:
                with open(self.discordBot.last_time_save_file, "w") as file:
                    json.dump(data, file, indent =4)
            except Exception as e:
                return

    # Place order and return the result (True : place the order,   False: error occurs)
    def place_order(self, signal, channel, account_index, channel_index) :
        ticker = signal['ticker']
        target_strike_price = signal['strike_price']
        price = signal['price']
        trade_type = signal['trade_type']
        desirable_expiration_date = signal['expiration_date']
        
        # Import the setting datas to get the threshold percent and delay time.
        with open('settings/setting.json', 'r') as json_file:
            saved_datas = json.load(json_file)

        if signal["ticker"] == "None" or signal["trade_type"] == "None" or signal["price"] == "None" or signal["strike_price"] == "None" :
            self.telegramBot.send_message(f"🔥The order was not placed.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {target_strike_price}\nReason: Invalid elements in buy signal.")
            return False
        # Search the fittable expirate date
        selected_expiration = self.robinhood[account_index].select_expiration_date(ticker, desirable_expiration_date)

        # Search the fittable strike price
        strike_price, expiration_date = self.robinhood[account_index].select_strike_price(ticker, target_strike_price, trade_type,  selected_expiration)
        
        # Fetch the option id.
        option_id = self.robinhood[account_index].get_option_id(
            ticker,
            strike_price,
            trade_type,
            expiration_date
        )

        # If no option , return False
        if option_id == None: return False
        if len(option_id)==0 : return False

        # Fetch the bid and ask price
        bid_price, ask_price, midpoint_price = self.robinhood[account_index].get_bid_ask_price(option_id[0])
        # Calculate the mid price
        
        threshold = float(saved_datas["threshold"][account_index])
        multify = (1+threshold/100)

        # If the initial ask price is over threshold
        if(ask_price > float(price)*multify) :
            self.telegramBot.send_message(f"Account {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: Initial buy-in price too high.")
            return False
        
        # Calculate the max contracts based on the cap price.
        channel_caps= saved_datas['cap_discord_channel'][account_index]
        cap = channel_caps[channel_index]
        max_contracts = int(float(cap) // (midpoint_price * 100))

        # Place the buy order
        self.robinhood[account_index].check_connect()
        order =self.robinhood[account_index].place_buy_limit_order(ticker, midpoint_price, max_contracts, selected_expiration, strike_price, trade_type)
        if order == "PDT":
            self.telegramBot.send_message(f"🔥The order was not placed.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: PDT warning.")
            return False
        if order == None:
            self.telegramBot.send_message(f"🔥The order was not placed.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: Can't place the order. Please check your account.")
            return False
        if hasattr(order, 'detail'):
            if(order['detail']=="You do not have enough overnight buying power to place this order."):
                self.telegramBot.send_message(f"🔥The order was not placed.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: Insufficient balance.")
                return False
            elif (order['detail']=="Price does not satisfy the min tick value."):
                self.telegramBot.send_message(f"🔥The order was not placed.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: Min tick error.")
                return False;
            
        if 'id' in order: # If the order is successful.
            self.telegramBot.send_message(f"🔥Order successful.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\n Order was placed successfully.")
            self.robinhood[account_index].orders.append(order['id'])
            print(f"Account {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\n Order was placed successfully.")
        else : # If the order fails.
            self.telegramBot.send_message(f"🔥The order was not placed.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: {order}")
            return False
        
        start_time = time.time()
        delay = float(saved_datas["delay"][account_index])
        while time.time() - start_time < delay:
            # Fetch the current ask price
            try:
                _ , current_ask_price, _ = self.robinhood[account_index].get_bid_ask_price(option_id[0])
                print("current_ask_price => ", current_ask_price)
                # If current ask price is over threshold : return False.
                if current_ask_price >= multify * float(price):
                    self.robinhood[account_index].cancel_order(int(order['id']))
                    self.robinhood[account_index].orders.remove(order['id'])
                    self.telegramBot.send_message(f"🔥The order was not triggered.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: Buy-in price increased too quickly.")
                    return False
                
                # If the order is filled : return True
                order_info = self.robinhood[account_index].get_order_info(order['id'])
                if order_info != None and order_info['state'] == 'filled':
                    return True
            except Exception as e:
                print(f"Error occurs: {e}")
                break
            time.sleep(1)
        # Cancel the order if not filled within delay seconds
        self.robinhood[account_index].cancel_order(order['id'])
        self.robinhood[account_index].orders.remove(order['id'])
        self.telegramBot.send_message(f"🔥The order was not triggered.\n\nAccount {saved_datas['accounts'][account_index]['account_number']}\nChannel: {channel.upper()}\nTicker: {ticker}\nStrike: {strike_price}\nReason: Buy order not filled in time.")
  
# Instance of class MyBot.
mybot = MyBot()
     
# Create a Flask application instance
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Define a route for the root URL
@app.route('/')
def hello_world():
    return 'Hello, World!'

# Get request of resume :   index: -1 => All,  index:(0,7) => Specific account
@app.route('/resume', methods=['GET'])
def resume() :
    index = request.args.get('id')
    mybot.resume(int(index))
    return "Resume"

# Get request of pause :   index: -1 => All,  index:(0,7) => Specific account
@app.route('/pause', methods = ['GET'])
def pause() :
    index = request.args.get('id')
    mybot.pause(int(index))
    return "Pause"

# Get request of sell :   index: -1 => All,  index:(0,7) => Specific account
@app.route('/sell',methods=['GET'])
def sell():
    index = request.args.get('id')
    mybot.on_sellall(int(index))
    return "Sell_all"

# Receive all setting datas from the front-end and save in the file.
@app.route('/save_settings',methods=['POST'])
def save_settings():
    param1 = request.args.get('data')
    if request.is_json:
        # Get the JSON data
        data = request.get_json()

    with open("settings/setting.json","w") as file:
        json.dump(data, file)
    # Re-check according to the new setting data.
    mybot.connect_check()
    return "Save settings"

# Send all setting datas to the front-end 
@app.route('/get_settings')
def get_settings():
    with open("settings/setting.json", "r") as file:
        datas= json.load(file)
    return datas

# Run the server
if __name__ == "__main__":
    # Launch the bot.
    try:
        mybot.on_start()

        # Launch the server
        app.run(host="0.0.0.0", port=8080)
    except Exception as e :
        print(f'Server error occurs. {e}')
        mybot.telegramBot.send_message(f"🔥The bot is closed!!!!")
        exit()
