import os
import requests
import json
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from configparser import ConfigParser
import time
# import asyncio
# import nest_asyncio


config = ConfigParser()
file_path ="config.ini"
config.read(file_path)

class DiscordBot:
    def __init__(self, channels, channel_ids, authorization):
        self.lasttimestamp = None
       
        self.channels = channels
        self.channel_ids = channel_ids
        self.authorization = authorization

        self.last_time_save_file = "last_time.json"
        if not os.path.exists(self.last_time_save_file):
            inital_last_time_str = '1900-01-01T00:00:00.000000+00:00'
            # last_time = datetime.fromisoformat(inital_last_time_str)
            data = {
                "et": inital_last_time_str,
                "dt": inital_last_time_str,
                "mm": inital_last_time_str,
                "sre": inital_last_time_str
            }
            try:
                with open(self.last_time_save_file, "w") as file:
                    json.dump(data, file, indent =4)
            except Exception as e:
                print(f'error=> {e}')
        print("DiscordBot Init...")
 
    def check_connection(self, channel_id, token): 
        headers = {
           'Authorization' : f"{token}",
           'Content-Type' : 'application/json'
        } 
        url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
        response = requests.get(url, headers=headers) 
        if response.status_code == 200:
           return True
        else:
           return False

    def getSignal_fromDiscord(self, channel, channel_id, token): 
        headers = {
           'Authorization' : token,
           'Content-Type' : 'application/json'
        } 
        url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
        response = requests.get(url, headers=headers) 
        if response.status_code == 200:
            messages = response.json()
            trades=[]
            for message in messages:
                try: 
                    with open(self.last_time_save_file, "r") as file:
                        last_time = json.load(file)
                    message_time = datetime.fromisoformat(message['timestamp'])
                    delay = (message_time-datetime.fromisoformat(last_time[channel])).total_seconds()
                    if delay<=0:
                        continue
                    
                except Exception as e:
                    print(e)
                    return None
                parsed_message= None
                if channel=="et" :
                    parsed_message = self.parse_et_messages(message['content'], message['timestamp'])
                elif channel == "dt":
                    parsed_message = self.parse_dt_messages(message['content'], message['timestamp'])
                elif channel == "mm" :
                    parsed_message = self.parse_mm_messages(message['content'], message['timestamp'])
                elif (channel == "sre" or channel == "sre_qa" or channel == "sre_pa") :
                    parsed_message = self.parse_sre_messages(message['content'], message['timestamp'])
                else :
                    continue
                if parsed_message==None :
                    continue
                trades.append(parsed_message)
                return trades
        else :
            print("No connect")
            return None
                

    #Parse ET messages into trade orders
    def parse_et_messages(self,message, timestamp) : 
        challenge_pattern = re.compile(r'.*\$100\s*To\s*\$10,000\s*Challenge.*', re.IGNORECASE)
        # trade_pattern = re.compile(r'\$([A-Z]+)\s(\d+)(c|p)\s@\.(\d+)')
        # trade_pattern = re.compile(r'.*(\d{1,2}/\d{1,2})\s+\$([A-Z]+)\s+(\d+)(c|p)\s+@(\d+(\.\d+)?)')
        trade_pattern = re.compile(r'(\d+/\d+)\s+\$(\w+)\s+(\d+)([c])\s+@((\d+)?\.\d+)')
        trades = None
        if challenge_pattern.search(message):
            match = trade_pattern.search(message)
            if match:
                expiration_date = self.change_date_format(match.group(1))
                # expiration_date = match.group(1)
                ticker = match.group(2)
                strike_price = match.group(3)
                trade_type = match.group(4).upper()
                price = match.group(5)
 
                trades={
                    'ticker' : ticker, 
                    'strike_price' : strike_price,
                    'trade_type' : 'Call' if trade_type =='C' else 'Put',
                    'price' : price,
                    'expiration_date' : expiration_date,
                    'timestamp' : timestamp
                }
        return trades

    #Parse DT messages into trade orders
    def parse_dt_messages(self, message, timestamp) :
        order_pattern = re.compile(r'^\$([A-Z]+)\s.*(?<!➡️)')
        trade_pattern = re.compile(r'^\$([A-Z]+)\n((\d{2}) (\w{3}) (\d{2})) \$([\d.]+)([cp])\s+\$((\d+)?\.\d+)')
        
        trades = None
        arr_month ={
            "Jan":1,
            "Feb":2,
            "Mar":3,
            "Apr":4,
            "May":5,
            "Jun":6,
            "Jul":7,
            "Aug":8,
            "Sep":9,
            "Oct":10,
            "Nov":11,
            "Dec":12,
        }
        if order_pattern.match(message) :
            match = trade_pattern.search(message)
            if match:
                ticker = match.group(1)
                day = match.group(3)
                month = match.group(4)
                year = match.group(5)
                strike_price = match.group(6)
                trade_type = match.group(7).upper() 
                price = match.group(8)
                
                # Parse the date string
                date_obj = datetime.strptime(f"{year}/{arr_month[month]}/{day}", "%y/%m/%d")
                # Format the date object to the desired output format
                formatted_date = date_obj.strftime("%Y-%m-%d")
                trades={
                    'ticker' : ticker,
                    'strike_price' : strike_price,
                    'trade_type' : 'Call' if trade_type == 'C' else 'Put',
                    'price':price,
                    'expiration_date':formatted_date,
                    'timestamp' : timestamp                
                }
        return trades

    # Parse MM messages into trade orders
    def parse_mm_messages(self, message, timestamp) :
        check_pattern  = re.compile(r'^\$(\w+).*(🚨).*') 
        trade_pattern = re.compile(r'^\$(\w+)\s+(\d+(\.\d+)?)\s+(CALL|PUT)\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+@\s+(\d+(\.\d+)?).*🚨')
        trades= None
        invalid_trades =[]
        if check_pattern.match(message):
            match = trade_pattern.search(message)
            if match:
                ticker = match.group(1)
                strike_price = match.group(2)
                trade_type = match.group(4).capitalize()
                expiration_date = self.change_date_format(match.group(5))
                price = match.group(6)

                trades={
                    'ticker' : ticker,
                    'strike_price' : strike_price,
                    'trade_type' : trade_type,
                    'price' : price,
                    'expiration_date' : expiration_date,
                    'timestamp' : timestamp
                }

        return trades


    # Parse SRE QT + PA messages into trade orders
    def parse_sre_messages(self,message, timestamp):
        trade_pattern = re.compile(
            r'(\d{1,2}/\d{1,2})\s\$(\w+)\s(Call|Put)\sat\s\$(\d+)\sat\s(\d+(\.\d+)?)\s.*@everyone|@everyone\s*\n*\n*(\d{1,2}/\d{1,2})\s\$(\w+)\s(Call|Put)\sat\s\$(\d+)\sat\s(\d+(\.\d+)?)'
        )
        # check_pattern = re.compile(r'.*@everyone\s*\n*\n*\d{1,2}/\d{1,2}\s\$(\w+).*(Call|Put).*|.*\$(\w+).*(Call|Put).*\s@everyone')
        check_pattern = re.compile(r'.*@everyone\s*\n*\n*\d{1,2}/\d{1,2}\s\$(\w+).*(Call|Put).*|.*\$(\w+).*(Call|Put).*\s@everyone')
        trades = None
        if check_pattern.match(message) :
            match = trade_pattern.search(message)
            if match:
                if match.group(1):
                    expiration_date = self.change_date_format(match.group(1))
                    ticker = match.group(2)
                    trade_type = match.group(3).capitalize()
                    strike_price = match.group(4)
                    price = match.group(5)
                else:
                    expiration_date = self.change_date_format(match.group(7))
                    ticker = match.group(8)
                    trade_type = match.group(9).capitalize()
                    strike_price = match.group(10)
                    price = match.group(11)
                trades={
                    'ticker': ticker,
                    'strike_price': strike_price,
                    'trade_type': trade_type,
                    'price': price,
                    'expiration_date': expiration_date,
                    'timestamp' : timestamp
                }
        return trades
        
    def change_date_format(self, date_str):
        # Get today's date
        today = datetime.today()

        # Parse the date string into a datetime object for the current year
        current_year = today.year
        parsed_date = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d")
        formatted_date = parsed_date.replace(year=current_year).strftime("%Y-%m-%d")
        
        return formatted_date