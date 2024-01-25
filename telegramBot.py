from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from requests import *
from dotenv import load_dotenv
import os
from os.path import join, dirname
import tradeBot as tb

#This class is used to start the telegram bot
class TelegramBot:
    def __init__(self):
        dotenv_path = join(dirname(__file__), '.env')
        load_dotenv(dotenv_path)
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.updater = Updater(token=self.token)
        self.dispatcher = self.updater.dispatcher

    ## This starts the bot and adds the handlers to the dispatcher.
    def start(self):
        if os.path.exists('instances.csv'):
            os.remove('instances.csv')
            with open('instances.csv', 'x'):pass # Creates the file if it doesn't exist

        newBot = tb.TradeBot() # Creates a new instance of the bot

        ## Handlers
        # Conversation handler for the start command
        CH = ConversationHandler(entry_points=[CommandHandler('start', newBot.startCommand)], 
        states= {1 : [CallbackQueryHandler(newBot.startCommand1stPair)],
                2 : [MessageHandler(Filters.text, newBot.startCommand2ndPair)],
                3 : [MessageHandler(Filters.text, newBot.startCommandPrice)],
                4 : [MessageHandler(Filters.text, newBot.startCommandCandlewick)],
                5 : [MessageHandler(Filters.text, newBot.startCommandVolume)],
                 6: [MessageHandler(Filters.text, newBot.startCommandLastCheck)],
                 7: [CallbackQueryHandler(newBot.startCommandInitialization)]},
        fallbacks= [MessageHandler(Filters.regex(r'Cancelar'), newBot.cancel)],
        allow_reentry=True)

        # Conversation handler for the stop command
        SB = ConversationHandler(entry_points=[CommandHandler('stop', newBot.stopCommand)], 
        states= {1 : [CallbackQueryHandler(newBot.stopCommandDeleteInstance)]},
        fallbacks= [MessageHandler(Filters.regex(r'Cancelar'), newBot.cancel)],
        allow_reentry=True)
        
        # Conversation handler for the edit command
        ED = ConversationHandler(entry_points=[CommandHandler('edit', newBot.editCommand)],
                                 states={1: [CallbackQueryHandler(newBot.editCommandSelectField)],
                                         2: [CallbackQueryHandler(newBot.editCommandIntroduceValue)],
                3 : [MessageHandler(Filters.text, newBot.editCommandPrice)],
                4 : [MessageHandler(Filters.text, newBot.editCommandCandlewick)],
            5: [MessageHandler(Filters.text, newBot.editCommandVolume)]},
        fallbacks= [MessageHandler(Filters.regex(r'Cancelar'), newBot.cancel)],
        allow_reentry=True)

        self.dispatcher.add_handler(ED)
        self.dispatcher.add_handler(SB)
        self.dispatcher.add_handler(CH)
        self.dispatcher.add_handler(CommandHandler('list', newBot.listCommand)) # Handler for the list command
        self.updater.start_polling()

