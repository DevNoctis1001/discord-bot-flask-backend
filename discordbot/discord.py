import requests
import json
import re
from datetime import datetime, timezone
import time
import os

class DiscordBot:
    # Construct of this class
    def __init__(self, channels, channel_ids, authorization):
        self.lasttimestamp = None
       
        self.channels = channels
        self.channel_ids = channel_ids
        self.authorization = authorization

        self.last_time_save_file = "last_time.json"
        if not os.path.exists(self.last_time_save_file):
            # last_time.json reset
            
            # Get the current local time
            local_time = datetime.now()

            # Define the GMT timezone
            gmt_timezone = pytz.timezone('GMT')

            # Convert local time to GMT
            gmt_time = local_time.astimezone(gmt_timezone)

            # Print the results
            print("Current Local Time:", local_time)
            print("Converted GMT Time:", gmt_time)
            gmt_time_string = gmt_time.strftime('%Y-%m-%dT%H:%M:%S')
            data = {
                    "et": gmt_time_string+"+00:00",
                    "dt": gmt_time_string+"+00:00",
                    "mm": gmt_time_string+"+00:00",
                    "sre_qt": gmt_time_string+"+00:00",
                    "sre_pa": gmt_time_string+"+00:00"
                }
            try:
                with open(self.last_time_save_file, "w") as file:
                    json.dump(data, file, indent =4)
            except Exception as e:
                print(f'error=> {e}')
        print("DiscordBot Init...")
 
    # Check the connection
    def check_connection(self, channel_id, token): 
        headers = {
           'Authorization' : f"{token}",
           'Content-Type' : 'application/json'
        } 
        url = f'https://discord.com/api/v10/channels/{int(channel_id)}/messages'
        response = requests.get(url, headers=headers) 
        if response.status_code == 200:
           return True
        else:
           return False

    # Fetch the signal from discord channel
    def getSignal_fromDiscord(self, channel, channel_id, token): 
        headers = {
           'Authorization' :  f"{token}",
           'Content-Type' : 'application/json'
        } 
        url = f'https://discord.com/api/v9/channels/{int(channel_id)}/messages'
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
                elif (channel == "sre" or channel == "sre_qt" or channel == "sre_pa") :
                    parsed_message = self.parse_sre_messages(message['content'], message['timestamp'])
                else :
                    continue
                if parsed_message==None :
                    continue
                print(f"----------{channel}-----------------------")
                trades.append(parsed_message)
                break
            return trades
        else :
            print("No connect")
            return None
                

    #Parse ET messages into trade orders
    def parse_et_messages(self,message, timestamp) : 
        # message = "🚀$100 TO $10,000 Challenge🚀\n\n🚀10/4 $CZR @.20 | 25 CONTRACTS🚀 @everyone"
        print(f'ET => {message} {timestamp}')
        challenge_pattern = re.compile(r'.*\$100\s*To\s*\$10,000\s*Challenge.*', re.IGNORECASE)
        trade_pattern = re.compile(r'(\d+/\d+)?\s*(\$(\w+))?\s*(\d+)?([c])?\s*@((\d+)?\.\d+)?')

        trades = None
        if challenge_pattern.search(message):
            match = trade_pattern.search(message)
            if match:
                expiration_date = match.group(1)
                # expiration_date = match.group(1)
                ticker = match.group(3)
                strike_price = match.group(4)
                trade_type = match.group(5)
                price = match.group(6)
 
                trades={
                    'ticker' : ticker if ticker else  'None', 
                    'strike_price' : strike_price if strike_price else  'None',
                    'trade_type' : ('Call' if trade_type.upper() =='C' else 'Put') if trade_type else 'None',
                    'price' : price if price else 'None',
                    'expiration_date' : self.change_date_format(expiration_date) if expiration_date else 'None',
                    'timestamp' : timestamp
                }
        print(f'Parsed message => {trades}')
        return trades

    #Parse DT messages into trade orders
    def parse_dt_messages(self, message, timestamp) :
        print(f"DT =>{message}------------------------\n")
        # Define the regex pattern
        pattern = re.compile(r'\$(\w+)\n((\d{1,2})\s+(\w+)\s+(\d{2}))?\s*(\s*\$([\d.]+)([c|p]?)\s*)?(\s*\$([\d.]+))?')
        order_pattern = re.compile(r'^\$([A-Z]+)\s.*(?<!➡️)')
        
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
        # Find matches in the message
        match = pattern.search(message)
 
        if order_pattern.match(message) :
            match = pattern.search(message)
            if match:
                ticker = match.group(1)             # Stock symbol
                day = match.group(3)                 # Day
                month = match.group(4)               # Month
                year = match.group(5)                # Year
                strike_price = match.group(7)        # Strike price (without 'c')
                trade_type = match.group(8)          # 'c' if exists, otherwise empty
                price = match.group(10)               # Additional price    
                
                formatted_date ='None'
                if year and month and day:
                # Parse the date string
                    date_obj = datetime.strptime(f"{year}/{arr_month[month]}/{day}", "%y/%m/%d")
                    # Format the date object to the desired output format
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                trades={
                    'ticker' : ticker if ticker else 'None',
                    'strike_price' : strike_price if strike_price else 'None',
                    'trade_type' : ('Call' if trade_type == 'c' else 'Put') if trade_type else 'None' ,
                    'price':price if price else 'None',
                    'expiration_date':formatted_date,
                    'timestamp' : timestamp                
                }
        print(f'Parsed message => {trades}')
        return trades

    # Parse MM messages into trade orders
    def parse_mm_messages(self, message, timestamp) :
        # message = "$CVS 67 CALL @ 0.42 DAY / SWING TRADE 🚨 @everyone"
        # Updated regex pattern to correctly capture components
        check_pattern = r'^\$(\w+).*🚨.*'
        pattern = r'^\$(\w+)\s*(\d+(\.\d+)?)?\s*(CALL|PUT)?\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\s*@\s*(\d+(\.\d+)?)?\s*(.*?)(🚨)?\s*(.*)?'
        # with open("mm.txt", "w", encoding="utf-8", errors="ignore") as ff:
        #     ff.write(f"MM => {message}")
        # Process each input string
        trades = None
        if re.match(check_pattern, message):
            match = re.match(pattern, message)

            if match:
                identifier = match.group(1)            # The stock identifier (e.g., CVS)
                strike_price = match.group(2)               # The quantity (e.g., 67)
                option_type = match.group(4)            # The option type (CALL/PUT)
                date = match.group(5)                   # The date (e.g., 10/11)
                price = match.group(6)                  # The price (e.g., 0.42) 
            
                trades={
                    'ticker' : identifier,
                    'strike_price' : strike_price if strike_price else 'None',
                    'trade_type' : option_type if option_type else 'None',
                    'price' : price if price else 'None',
                    'expiration_date' : self.change_date_format(date) if date else 'None',
                    'timestamp' : timestamp
                }
                # ff.write(f"parsed message => {trades}" )
            else:
                print("No match found.")

        return trades


    # Parse SRE QT + PA messages into trade orders
    def parse_sre_messages(self,message, timestamp):
        # with open("sre.txt","w", encoding = "utf-8" , errors="ignore") as ff:
        # There’s 100% on $IWM @everyone
        # SRE ="3pm flush trade. Hoping for a collapse @everyone \n\n10/8 $QQQ Put at $489 at 0.63"
        print(f'SRE => {message}\n')
        trade_pattern = re.compile(
            r'(\d{1,2}/\d{1,2})?\s\$(\w+)?(\s(Call|Put))?(\sat\s\$(\d+(\.\d+)?))?(\sat\s(\d+(\.\d+)?))?\s.*@everyone|@everyone\s*\n*\n*(\d{1,2}/\d{1,2})?\s\$(\w+)?(\s(Call|Put))?(\sat\s\$(\d+(\.\d+)?))?(\sat\s(\d+(\.\d+)))?'
        )
        check_pattern = re.compile(r'.*@everyone\s*\n*.*\$(\w+)\s+(Put|Call).*|.*\$(\w+)\s+(Put|Call).*\s*\n*@everyone')
        trades = None
        if check_pattern.search(message):
            match = trade_pattern.search(message)
            if match:
                if match.group(1):
                    expiration_date = match.group(1)
                    ticker = match.group(2)
                    trade_type = match.group(4)
                    strike_price = match.group(6)
                    price = match.group(9)
                else:
                    expiration_date = match.group(11)
                    ticker = match.group(12)
                    trade_type = match.group(14)
                    strike_price = match.group(16)
                    price = match.group(19)
                # ff.write(f'----------------------------\nstrike_price => {strike_price}\n----------------------------\n')
                trades={
                    'ticker': ticker if ticker else 'None',
                    'strike_price': strike_price if strike_price else 'None',
                    'trade_type': trade_type.capitalize() if trade_type else 'None',
                    'price': price if price else 'None',
                    'expiration_date':self.change_date_format(expiration_date) if expiration_date else 'None',
                    'timestamp' : timestamp
                }
        print(f'Parsed message => {trades}')
        return trades
        
    # Change the date format "%m/%d" => "%Y-%m-%d"
    def change_date_format(self, date_str):
        # Get today's date
        today = datetime.today()

        # Parse the date string into a datetime object for the current year
        current_year = today.year
        parsed_date = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d")
        formatted_date = parsed_date.replace(year=current_year).strftime("%Y-%m-%d")
        
        return formatted_date