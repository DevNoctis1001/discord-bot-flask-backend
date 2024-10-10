import re

def test_mm():
    # Define the input strings
    input_strings = [
        "$CVS 67.5 CALL 10/11 @ 0.42 DAY / SWING TRADE ❤️ @everyone",
        "$CVS CALL 10/11 @ 0.42 DAY / SWING TRADE ❤️ @everyone",
        "$CVS 67 10/11 @ 0.42 DAY / SWING TRADE ❤️ @everyone",
        "$CVS 67 CALL @ 0.42 DAY / SWING TRADE ❤️ @everyone",
        "$CVS 67.2 CALL 10/11 DAY / SWING TRADE ❤️ @everyone",
        "$CVS 10/11 @ 0.42 DAY / SWING TRADE ❤️ @everyone",
        "$CVS CALL @ 0.42 DAY / SWING TRADE ❤️ @everyone",
        "$CVS CALL 10/11 DAY / SWING TRADE ❤️ @everyone"
    ]

    # Updated regex pattern to correctly capture components
    pattern = r'^\$(\w+)\s*(\d+(\.\d+)?)?\s*(CALL|PUT)?\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)?\s*@\s*(\d+(\.\d+)?)?\s*(.*?)(❤️)?\s*(.*)?'

    # Process each input string
    for input_string in input_strings:
        match = re.match(pattern, input_string)

        if match:
            identifier = match.group(1)            # The stock identifier (e.g., CVS)
            quantity = match.group(2)               # The quantity (e.g., 67)
            option_type = match.group(4)            # The option type (CALL/PUT)
            date = match.group(5)                   # The date (e.g., 10/11)
            price = match.group(6)                  # The price (e.g., 0.42)
            additional_info = match.group(8)        # Additional info (e.g., "DAY / SWING TRADE")
            mention = match.group(10)                # Mention (@everyone)

            # Print extracted components
            print(f"Input String: {input_string}")
            print(f"Identifier: {identifier}")
            print(f"Quantity: {quantity if quantity else 'None'}")
            print(f"Option Type: {option_type if option_type else 'None'}")
            print(f"Date: {date if date else 'None'}")
            print(f"Price: {price if price else 'None'}")
            print(f"Additional Info: {additional_info.strip() if additional_info else 'None'}")
            print(f"Mention: {mention if mention else 'None'}")
            print("-" * 40)
        else:
            print("No match found.")

def test_sre() :
    # Define the input string
    input_string = "10/8 $IWM Put at $218 at 0.23"

    # Define a regex pattern to match components, ensuring @everyone and ticker are present
    pattern = r'(\d{1,2}/\d{1,2})?\s*\$([A-Z]+)\s*(CALL|PUT)?\s*at\s*\$?(\d+(\.\d+)?)?|(\d{1,2}/\d{1,2})?\s*\$([A-Z]+)\s*(CALL|PUT)?\s*at\s*\$?(\d+(\.\d+)?)?\s*'

    # Use re.search to extract components
    match = re.search(pattern, input_string)

    if match:
        mention = match.group(1) or match.group(7)  # The mention (@everyone)
        date = match.group(2) or match.group(6)      # The date (e.g., 10/8)
        ticker = match.group(3) or match.group(8)    # The stock ticker (e.g., IWM)
        option_type = match.group(4) or match.group(9)  # The option type (CALL/PUT)
        price = match.group(5) or match.group(10)     # The price (e.g., 218 or 0.23)

        # Print extracted components
        print(f"Mention: {mention if mention else 'None'}")
        print(f"Date: {date if date else 'None'}")
        print(f"Ticker: {ticker if ticker else 'None'}")
        print(f"Option Type: {option_type if option_type else 'None'}")
        print(f"Price: {price if price else 'None'}")
    else:
        print("No match found.")


# Parse SRE QT + PA messages into trade orders
def parse_sre_messages():
    # message ="Todays gameplan $SPY @everyone \n\nI’m actually sticking to my first instinct. Yesterday night I was thinking calls, I didn’t take it yesterday bc we gapped up and pumped. I’m not changing my first idea\n\nLast night I was thinking puts because we pumped to all time highs with no pull backs \n\nThe Puts in watching today\n10/9 $SPY Put at $570"
    message = "Todays gameplan $SPY @everyone \n\n10/9 $SPY Put at $570"
    
    print(f'SRE => {message}\n')
    trade_pattern = re.compile(
        r'(\d{1,2}/\d{1,2})?\s\$(\w+)?(\s(Call|Put))?(\sat\s\$(\d+(\.\d+)?))?(\sat\s(\d+(\.\d+)?))?\s.*@everyone|@everyone\s*\n*(\d{1,2}/\d{1,2})?\s\$(\w+)?(\s(Call|Put))?(\sat\s\$(\d+(\.\d+)?))?(\sat\s(\d+(\.\d+)))?'
    )
    check_pattern = re.compile(r'.*(\$)?.*@everyone\s*\n*.*\$(\w+)\s+(Put|Call).*|.*\$(\w+)\s+(Put|Call).*(\$)?.*\s*\n*@everyone')
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
                'expiration_date':expiration_date if expiration_date else 'None'
                # 'timestamp' : timestamp
            }
    print(f'Parsed message => {trades}')
    return trades
    
def parse_dt_message():
    # Define the message
    message = "$HD\n11 Oct 24 $417.5c"

    # Define the regex pattern
    pattern = re.compile(r'\$(\w+)\n((\d{1,2})\s+(\w+)\s+(\d{2}))?\s*(\s*\$([\d.]+)([c|p]?)\s*)?(\s*\$([\d.]+))?')

    # Find matches in the message
    match = pattern.search(message)

    # Extracting and printing the results
    if match:
        ticker = match.group(1)             # Stock symbol
        day = match.group(3)                 # Day
        month = match.group(4)               # Month
        year = match.group(5)                # Year
        strike_price = match.group(7)        # Strike price (without 'c')
        trade_type = match.group(8)          # 'c' if exists, otherwise empty
        price = match.group(10)               # Additional price

        print(f"ticker: {ticker}")
        print(f"day: {day}")
        print(f"month: {month}")
        print(f"year: {year}")
        print(f"strike_price: {strike_price}")
        print(f"trade_type: {trade_type if trade_type else 'N/A'}")
        print(f"price: {price if price else 'N/A'}")
    else:
        print("No match found.")
parse_sre_messages()