import robin_stocks.robinhood as rh
from datetime import datetime,timedelta, timezone
import pytz
import json
import time
import pyotp

class RobinhoodClient :
    def __init__(self, username, password, totp, account_type, account_number) :
        self.username = username
        self.password = password
        self.totp = totp
        self.account_type = account_type
        self.account_number= account_number
        self.is_connect = False
        self.token = None
        self.orders=[]

    # Check the connect of the robinhood account
    def check_connect(self):
        try:
            mfa= pyotp.TOTP(self.totp).now()
            result = rh.login(username = self.username, password = self.password, by_sms=True, store_session = False, mfa_code = mfa)
            self.token = result['access_token']
            return True
        except Exception as e:
            print(f"Failed to login to Robinhood: {e}")  
            return False
    
    # Fetch all option for the ticker on the chain.
    def get_options_chain(self, ticker):
        options = rh.options.get_chains(ticker) 
        return options
    
    # Fetch the option id.
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
    
    # Sell the opened positions.
    def sell_all(self) : 
        print(f'Account number =>{self.account_number}')

        if self.account_number==None :return

        # Fetch all opened positions in the current account.
        positions = rh.options.get_open_option_positions(str(self.account_number))
        print(f"Print positions= {positions}")
        for order in self.orders:
            self.cancel_order(order)

        if len(positions)==0 : return
        # print(f"openned potion ->{positions}")
        # Sell all opened positions in the market price
        for position in positions['results']:  
            quantity = position['quantity']  
            if quantity > 0:  
                response = rh.order_sell_market(
                    symbol=position['instrument']['symbol'],
                    quantity=position['quantity'],
                    option_type=position['option_type'],
                    strike_price=position['strike_price'],
                    expiration_date=position['expiration_date']
                )
                print("Order Response:", response)
                print(f"Sold {quantity} shares of {position['instrument']['symbol']}")
            time.sleep(1)

    # Get the bid and ask price of the option by the option id.
    def get_bid_ask_price(self, option_id) :
        try:
            quote = rh.options.get_option_market_data_by_id(str(option_id))
            if not quote or len(quote) != 1:
                raise ValueError(f"Unexpected number of items in quote date: {len(quote)}. Expected exactly on dictionary.")
            # print("quoto => ",quote[0])
            bid_price = float(quote[0].get('bid_price', 0))
            ask_price = float(quote[0].get('ask_price', 0 ))
            mid_price = float(quote[0].get('adjusted_mark_price_round_down',0))
            return bid_price, ask_price, mid_price
        except Exception as e:
            print(f"Error: {e}")
            return -1
            
    # Place buy limit order
    def place_buy_limit_order(self, symbol, limit_price, quantity, expiration_date, strike_price, trade_type):
        try:
            print(f'------ORDER_BUY_LIMIT-----------\n{symbol} {expiration_date} {strike_price} {trade_type.lower()} {quantity} {limit_price} {self.account_number}\n---------------------')
            order = rh.orders.order_buy_option_limit(
                positionEffect='open',
                creditOrDebit='debit',
                price=round(limit_price,3),
                symbol=symbol,
                quantity=min(quantity,500),
                expirationDate=expiration_date,
                strike=float(strike_price),
                optionType=trade_type.lower(),
                timeInForce='gtc',
                account_number=str(self.account_number)
            ) 
            return order
            
        except Exception as e:  
            if "Pattern Day Trader" in str(e):
                return "PDT"
            else :
                return str(e)
    
    # Cancel the order by order id.
    def cancel_order(self, order_id):
        print("canceling order : ", order_id) 

        try:
            order = rh.orders.cancel_option_order(str(order_id))
            return order
        except Exception as e:
            print(f"An error occurred while canceling the order with ID {order_id}: {e}")
            return None

    # Check if the expiration date is valid
    def is_valid_expiration(self,date_str) :
        
        with open('settings/setting.json', 'r') as json_file:
            saved_datas = json.load(json_file)
        date_obj= datetime.strptime(date_str, "%Y-%m-%d")
        holidays = saved_datas["holidays"]
        # If date is holiday : return False
        if date_str in holidays : return False   # Holiday
        # If date is weekend: return False
        return date_obj.weekday() <5 #0-4 are weekdays(Monday-Friday)

    # Return valid expiration dates for the symbol
    def get_valid_expiration_dates(self, symbol):
        option_data = rh.options.get_chains(symbol)
        if option_data == None : return
        # If symbol is in chain, return all expiration dates.
        expiration_dates = option_data['expiration_dates'] if option_data != None else []
        #Filter valid expiration dates
        valid_dates = [date for date in expiration_dates if self.is_valid_expiration(date)]

        return valid_dates

    # Return vaild expiration date for the desirable date.
    def select_expiration_date(self, ticker, desirable_expiration_date):
        # Get valid expiration dates for the symbol
        valid_dates = self.get_valid_expiration_dates(ticker)
        
        # If desirable expiration is in valid_dates: return itself.
        if desirable_expiration_date in valid_dates:
            return desirable_expiration_date

        tz_CentralTime = pytz.timezone('US/Central')
        today = datetime.now(tz_CentralTime)
        current_week_dates = [date for date in valid_dates if today<=datetime.strptime(date,"%Y-%m-%d").replace(tzinfo = tz_CentralTime)<today+timedelta(days=7)]

        # Return current week_date's expiration date.
        if current_week_dates:
            return current_week_dates[0]
        
        # return today date(daily).
        return today.strftime("%Y-%m-%d")
    
    #Get option chain data according to the symbol.
    def get_option_chain(self, symbol, trade_type, expiration_date):
        return rh.options.find_options_by_expiration(symbol, expirationDate =expiration_date, optionType=trade_type.lower())

    #Find ATM option.
    def find_at_the_money_option(self, options, current_price) :
        # Check if options list is empty
        if not options:
            raise ValueError("Options list is empty. No available options for this ticker.")
        # Find the closest option
        else :
            closest_option = min(options, key=lambda x: abs(float(x['strike_price']) - float(current_price)))
            return closest_option

    # Purchase at the money option
    def purchase_at_the_money_option(self, symbol, current_price, target_strike_price, trade_type, expiration_date):
        options = self.get_option_chain(symbol, trade_type, expiration_date)
        strike_prices =[float(option['strike_price']) for option in options]
        if float(target_strike_price) not in strike_prices:
            atm_option = self.find_at_the_money_option(options, current_price)
            strike_price_to_purchase = atm_option['strike_price']
            expiration_date= atm_option['expiration_date']
            option_id = atm_option['id']
            return strike_price_to_purchase, expiration_date
        else :
            return target_strike_price, expiration_date

    # Find the fittable strike price(If the target_strike_price is on the chain: return itself, else: return at the money.)
    def select_strike_price(self, ticker, target_strike_price, trade_type, selected_expiration) :
        try:
            current_price = rh.stocks.get_latest_price(ticker)[0]
            return self.purchase_at_the_money_option(ticker, current_price, target_strike_price, trade_type,selected_expiration)
        except Exception as e:
            print(f"In select_strike_price, error occurs:  {e}")
            return 'None', 'None'

    # Get the order info by the id
    def get_order_info(self, order_id):
        # print(order_id)
        try:
            order_info = rh.orders.get_option_order_info(order_id)
            # print(order_info)
            return order_info
            # return order_info[0]  # first dictionary only
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
    