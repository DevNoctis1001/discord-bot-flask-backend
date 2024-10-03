import telepot
import os

class TelegramBot :
    def __init__(self, token, chat_id) :
        self.token =token
        self.chat_id = chat_id

    def send_message(self,message) :
        bot = telepot.Bot(self.token)
        bot.sendMessage(self.chat_id, message)
