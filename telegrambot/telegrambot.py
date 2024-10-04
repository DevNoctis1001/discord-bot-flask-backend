import telepot
import os

class TelegramBot :
    def __init__(self, token, chat_id) :
        self.token =token
        self.chat_id = chat_id
    def check_telegram(self):
        try:
            bot=telepot.Bot(self.token)
            bot.sendMessage(int(self.chat_id),"Hi. This is a message confirming your connection to Telegram.")
            return True
        except Exception as e:
            print("Telegram connect error => ", e)
            return False
    def send_message(self,message) :
        try:
            bot = telepot.Bot(self.token)
            bot.sendMessage(int(self.chat_id), message)
        except Exception as e:
            print("Sending telegram message error.")
