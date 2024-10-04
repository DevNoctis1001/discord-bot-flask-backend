import robin_stocks.robinhood as rh
import os
from datetime import datetime,timedelta, timezone
from dotenv import load_dotenv
from configparser import ConfigParser
import pytz
import json

config = ConfigParser()
file_path ="config.ini"
config.read(file_path)

with open('settings/setting.json', 'r') as json_file:
    saved_datas = json.load(json_file)
class RobinhoodClient :
    def __init__(self, username, password, mfa, account_type, account_number) :
        self.username = username
        self.password = password
        self.mfa_code = mfa
        self.account_type = None
        self.account_number= None
        self.is_connect = False
        
    def check_connect(self):
        try:
            result = rh.login(username = self.username, password = self.password, by_sms=True, store_session = False, mfa_code = self.mfa_code)
            # print(result)
            return True
        except Exception as e:
            print(f"Failed to login to Robinhood: {e}")  
            return False
    #Check today's market hours and if it is opend : True/False
    def check_market_hours(self):
        try :
            now= datetime.now()
            market_hours = rh.markets.get_market_today_hours("XNYS")
            market_start = datetime.strptime(market_hours['opens_at'], "%Y-%m-%dT%H:%M:%SZ").time()
            market_end = datetime.strptime(market_hours["closes_at"], "%Y-%m-%dT%H:%M:%SZ").time()
            print(f'now: {now}  market_start : {market_start}   market_end : {market_end}')
            return market_start <= now.time() <=market_end
        except Exception as e:
            print(f"An error occured while checking market hours : {e}")
            return False
    def get_options_chain(self, ticker):
        options = rh.options.get_chains(ticker) 
        return options
    
    def get_option_id(self, ticker, strike_price, trade_type, expiration_date):
        try:
            option_id = rh.options.find_options_by_expiration_and_strike(
                ticker,
                expirationDate = expiration_date,
                strikePrice = strike_price,
                optionType = trade_type,
                info='id'
            )
            if option_id==None: return None
            return option_id
        except Exception as e:
            print(f"An error occured while getting the option ID: {e}")
            return None
   
    def sell_all(self) : 
        print(self.account_number, "  account_number" )
        if self.account_number==None :return
        positions = rh.options.get_open_option_positions(self.account_number)
        if len(positions)==0 : return
# positions = get_positions()  
        for position in positions['results']:  
            symbol = position['instrument']['symbol']  
            quantity = position['quantity']  
            if quantity > 0:  
                response = place_order(
                    symbol=symbol,
                    quantity=quantity,
                    side='sell',
                    type='market',
                    time_in_force='gfd'
                )
                print(f"Sold {quantity} shares of {symbol}")
            time.sleep(1)
        # print(positions)

    def get_bid_ask_price(self, option_id) :
        try:
            quote = rh.options.get_option_market_data_by_id(option_id)
            if not quote or len(quote) != 1:
                raise ValueError(f"Unexpected number of items in quote date: {len(quote)}. Expected exactly on dictionary.")
            bid_price = float(quote[0].get('bid_price', 0))
            ask_price = float(quote[0].get('ask_price', 0 ))
            return bid_price, ask_price
        except Exception as e:
            print(f"Error: {e}")
            return -1
            
    def order_buy_limit(self, symbol, expiration_date, strike_price, trade_type, quantity, limitPrice):
        try:
            print(f'------ORDER_BUY_LIMIT-----------\n{symbol} {expiration_date} {strike_price} {trade_type.lower()} {quantity} {limitPrice} {self.account_number}\n---------------------')
            order = rh.orders.order_buy_option_limit(
                positionEffect='open',
                creditOrDebit='debit',
                price=round(limitPrice,3),
                symbol=symbol,
                quantity=min(quantity,500),
                expirationDate=expiration_date,
                strike=float(strike_price),
                optionType=trade_type.lower(),
                timeInForce='gtc',
                account_number=self.account_number
            )
            return order
            
        except Exception as e:  
            return str(e)
    
    def cancel_order(self, order_id):
        try:
            order = rh.orders.cancel_option_order(order_id)
            return order
        except Exception as e:
            print(f"An error occurred while canceling the order with ID {order_id}: {e}")
            return None

    def is_valid_expiration(self,date_str) :
        date_obj= datetime.strptime(date_str, "%Y-%m-%d")
        holidays = saved_datas["holidays"]
        if date_str in holidays : return False   # Holiday
        return date_obj.weekday() <5 #0-4 are weekdays(Monday-Friday)

    def get_valid_expiration_dates(self, symbol):
        option_data = rh.options.get_chains(symbol)
        if option_data == None : return
        expiration_dates = option_data['expiration_dates'] if option_data != None else []
        #Filter valid expiration dates
        valid_dates = [date for date in expiration_dates if self.is_valid_expiration(date)]

        return valid_dates

    def select_expiration_date(self, ticker, desirable_expiration_date):
        valid_dates = self.get_valid_expiration_dates(ticker)
        
        if desirable_expiration_date in valid_dates:
            return desirable_expiration_date

        tz_CentralTime = pytz.timezone('US/Central')
        today = datetime.now(tz_CentralTime)
        current_week_dates = [date for date in valid_dates if today<=datetime.strptime(date,"%Y-%m-%d").replace(tzinfo = tz_CentralTime)<today+timedelta(days=7)]

        if current_week_dates:
            return current_week_dates[0]
        
        return today.strftime("%Y-%m-%d")


    def get_order_info(self, order_id):
        try:
            order_info = rh.orders.get_option_order_info(order_id)
            print(f"--------ORDER INFO--------------\n{order_info}\n-------------------------",order_info)
            # if order_info
            return order_info[0]  # first dictionary only
        except Exception as e:
            print(f"An error occurred while getting order info for ID {order_id}: {e}")
            return None
    #Check users's cash
    def check_cash(self) :
        try :
            my_profile = rh.account.build_user_profile()
            return float(my_profile['cash'])
        except Exception as e :
            print(f'An error occured while checking cash balance: {e}')
            return None
    
    #Get option market data
    def get_option_market_data(self, date, option_type, strike_price, list_of_options):
        try:
            all_options = []
            tradable_options = rh.options.find_tradable_options('AAPL', 
                                 expirationDate=None,
                                 strikePrice=400,
                                 optionType='call')
            # return
            print(tradable_options)

            # for item in option_data: 
            #     options_details = {
            #         'price' :                       item.get('strike_price'),
            #         'expiration_date' :             item.get('expiration_date'),
            #         'symbol' :                      item.get('chain_symbol'),
            #         'delta' :                       item.get('delta'),
            #         'theta' :                       item.get('theda'),
            #         'id' :                          item.get('id'),
            #         'strike_price' :                item.get('strike_price'),
            #         'ask_price' :                   item.get('ask_price'),
            #         'bid_price' :                   item.get('bid_price'),
            #         'mark_price':                   item.get('mark_price'),
            #         'last_trade_price':             item.get('last_trade_price'),
            #         'high_fill_rate_buy_price' :    item.get('high_fill_rate_buy_price'),
            #         'high_fill_rate_sell_price' :   item.get('high_fill_rate_sell_price'),
            #         'low_fill_rate_buy_price' :     item.get('low_fill_rate_buy_price'),
            #         'low_fill_rate_sell_price' :    item.get('low_fill_rate_sell_price')
            #     }
            #     all_options.append(options_details)
            return all_options #list of dicts

        except Exception as e: 
            print(f'An error occured while getting option market data: {e}')
            return None