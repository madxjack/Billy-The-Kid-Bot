from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from requests import *
from dotenv import load_dotenv
import os
import autoJumper as aj
import threading
import pandas as pd


## Class for the bot instance with a specific pair
#! Must be used after TelegramBot class is initialized and started with every new instance
class TradeBot:
    def __init__(self):
        load_dotenv()
        self.pair = ''
        self.pair1 = ''
        self.pair2 = ''
        self.price = 0
        self.topPrice = 0
        self.volume = 0
        self.authorized = int(os.getenv('TELEGRAM_GROUP_ID'))

    ## Check if the chat id is authorized to use the bot
    def checkAutorized(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if chat_id != self.authorized:
            context.bot.send_message(
                chat_id=self.authorized, text=f'Intento de uso no autorizado de {chat_id}.')
            return False
        return True

    #* Start command functions
    ## Start command
    def startCommand(self, update: Update, context: CallbackContext):
        if not self.checkAutorized(update, context):
            return ConversationHandler.END

        buttons = [[InlineKeyboardButton('Introducir pair', callback_data=1)], [InlineKeyboardButton('Ver bots iniciados', callback_data=2)],
                   [InlineKeyboardButton('Cancelar', callback_data=3)]]
        reply_markup = InlineKeyboardMarkup(buttons)
        update.message.reply_text(
            'Iniciando instancia... \nSelecciona una opción:', reply_markup=reply_markup)
        return 1

    ## Start command 1st menu
    def startCommand1stPair(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text=f"Inicializando bot")

        if query.data == '1':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Escribe el 1er pair:')
            return 2
        elif query.data == '2':
            self.listCommand(update, context)
            return 2
        elif query.data == '3':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Inicio cancelado.')
            return ConversationHandler.END

    ## Start command 2nd menu
    def startCommand2ndPair(self, update: Update, context: CallbackContext):
        pair = update.message.text
        if pair == 'Cancelar':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Inicio cancelado.')
            return ConversationHandler.END
        pair = pair.upper()
        context.user_data['pair1'] = pair
        self.pair1 = pair
        # context.bot.send_message(chat_id=update.effective_chat.id, text=f'Pair 1 seleccionado : {pair.upper()}')
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f'Introduce el 2do pair:')
        return 3

    ## Start command 3rd menu
    def startCommandPrice(self, update: Update, context: CallbackContext):
        pair = update.message.text
        if pair == 'Cancelar':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Saliendo...')
            return ConversationHandler.END
        pair = pair.upper()
        context.user_data['pair2'] = pair
        self.pair2 = pair

        if self.startCommandCheckInstanceOn():
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Ya existe una instancia con este par.')
            return ConversationHandler.END

        self.pair = self.pair1 + '/' + self.pair2
        context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f'Introduce el precio de compra para {self.pair}: ')
        return 4

    ## Start command 4th menu
    def startCommandCandlewick(self, update: Update, context: CallbackContext):
        price = update.message.text
        if price == 'Cancelar':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Saliendo...')
            return ConversationHandler.END
        context.user_data['price'] = price
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f'Introduce % min de pabilo {self.pair}: ')
        return 5

    ## Start command 5th menu
    def startCommandVolume(self, update: Update, context: CallbackContext):
        topPrice = update.message.text
        if topPrice == 'Cancelar':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Saliendo...')
            return ConversationHandler.END
        context.user_data['topPrice'] = topPrice
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f'Introduce volumen de {self.pair} para comprar: ')
        return 6

    ## Start command 6th menu
    def startCommandLastCheck(self, update: Update, context: CallbackContext):
        volume = update.message.text
        if volume == 'Cancelar':
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='Saliendo...')
            return ConversationHandler.END
        context.user_data['volume'] = volume
        
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Bot inicializado correctamente. \n'
                                 f'Pair: {context.user_data["pair1"].upper()}/{context.user_data["pair2"].upper()} \n'
                                 f'Precio: {context.user_data["price"]} \n%Min pabilo: {context.user_data["topPrice"]} \nVolumen: {context.user_data["volume"]}')

        buttons = [[InlineKeyboardButton('Inicializar bot.', callback_data=1)], [
            InlineKeyboardButton('Cancelar', callback_data=2)]]
        reply_markup = InlineKeyboardMarkup(buttons)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='¿Deseas inicializar el bot?', reply_markup=reply_markup)
        return 7

    ## Start command 7th option
    def startCommandInitialization(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()

        if query.data == '1':
            save = self.startCommandSaveNewInstance(update, context)
            if save:
                query.edit_message_text(text=f"Bot on!")
            else:
                query.edit_message_text(text=f"Error al iniciar el bot.")
            return ConversationHandler.END
        elif query.data == '2':
            query.edit_message_text(text=f"Inicio cancelado!")
            return ConversationHandler.END
    
    ## Save instance data and start new instance of autoJumper class
    def startCommandSaveNewInstance(self, update: Update, context: CallbackContext):
        save = False
        self.instance = {'pair1': context.user_data['pair1'], 'pair2': context.user_data['pair2'],
                         'price': context.user_data['price'], 'topPrice': context.user_data['topPrice'],
                         'volume': context.user_data['volume'], 'status': 1}

        if not self.startCommandCheckInstanceOn():
            self.startCommandSaveInstanceToCSV(self.instance)
            if os.path.exists(f'edit_{self.pair1}_{self.pair2}.csv'):   # Check if edit file in this pair exists
                os.remove(f'edit_{self.pair1}_{self.pair2}.csv')        # and delete it before create a new instance
            self.startCommandNewBotInstance()
            save = True
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=f'Ya existe un bot con esa configuración.')
        return save
    
    # Save instance to CSV file instances.csv
    def startCommandSaveInstanceToCSV(self, instance):
        columns = ['pair1', 'pair2', 'price', 'topPrice', 'volume', 'status']
        instances = self.getInstancesFromCSV()
        try:
            if instances.empty:
                df = pd.DataFrame(instance, columns=columns, index=[0])
                df.to_csv('instances.csv', index=False, header=False)
            else:
                df = pd.DataFrame(instance, columns=columns, index=[0])
                data = [instances, df]
                dfs = pd.concat(data, ignore_index=True)
                dfs.to_csv('instances.csv', index=False, header=False)
            return True
        except Exception as e:
            print(e)
            return False

    ## Create new instance autoJumper class in a new thread
    def startCommandNewBotInstance(self):
        newBot = aj.AutoJumper(self.instance['pair1'], self.instance['pair2'],
                               self.instance['price'], self.instance['topPrice'], self.instance['volume'])
        threading.Thread(target=newBot.start(),
                         name=self.instance['pair1'] + self.instance['pair2'])
        
    ## Check if instance is already on
    def startCommandCheckInstanceOn(self):
        instances = self.getInstancesFromCSV()
        if len(instances) == 0:
            return False
        else:
            for i in range(len(instances)):
                if instances['pair1'][i] == self.pair1 and instances['pair2'][i] == self.pair2:
                    return True
            return False
        
    #* Stop command functions
    ## Stop command - Show buttons with instances on to delete
    def stopCommand(self, update: Update, context: CallbackContext) -> None:
        if not self.checkAutorized(update, context):
            return ConversationHandler.END
        markup = []
        instances = self.getInstancesFromCSV()
        if len(instances) == 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='No hay bots iniciados.')
        else:
            for i in range(len(instances)):
                markup.append([InlineKeyboardButton(text=instances['pair1'][i] + '/' + instances['pair2'][i],
                                                    callback_data=instances['pair1'][i] + '/' + instances['pair2'][i])])

            replyMarkup = InlineKeyboardMarkup(markup)
            update.message.reply_text(
                'Selecciona un bot para eliminar', reply_markup=replyMarkup)

        return 1
    
    ## Stop command - Delete instance from CSV file instances.csv
    def stopCommandDeleteInstance(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()

        pair1 = query.data.split('/')[0]
        pair2 = query.data.split('/')[1]

        instances = self.getInstancesFromCSV()
        if len(instances) == 0:
            query.edit_message_text(text=f"No hay bots iniciados")

        else:
            for i in range(len(instances)):
                if instances['pair1'][i] == pair1 and instances['pair2'][i] == pair2:
                    instances = instances.drop([i])
                    instances.to_csv(
                        'instances.csv', index=False, header=False)
                    query.edit_message_text(
                        text=f"Bot {pair1}/{pair2} eliminado")

        return ConversationHandler.END

    #* List command function
    ## List command - Show instances on
    def listCommand(self, update: Update, context: CallbackContext) -> None:
        if not self.checkAutorized(update, context):
            return ConversationHandler.END
        instances = self.getInstancesFromCSV()
        if len(instances) == 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='No hay bots iniciados.')
        else:
            for i in range(len(instances)):
                pair1 = instances['pair1'][i]
                pair2 = instances['pair2'][i]
                pair = pair1 + '/' + pair2
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f'Bot en {pair} iniciado.')

    #* Edit command functions
    ## Edit command start 
    def editCommand(self, update: Update, context: CallbackContext) -> None:
        if not self.checkAutorized(update, context):
            return ConversationHandler.END
        markup = []
        instances = self.getInstancesFromCSV()
        if len(instances) == 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='No hay bots iniciados.')
            return ConversationHandler.END
        else:
            for i in range(len(instances)):
                markup.append([InlineKeyboardButton(text=instances['pair1'][i] + '/' + instances['pair2'][i],
                                                    callback_data=instances['pair1'][i] + '/' + instances['pair2'][i])])

            replyMarkup = InlineKeyboardMarkup(markup)
            update.message.reply_text(
                'Selecciona un bot para editar', reply_markup=replyMarkup)

        return 1

    ## Edit command 1st option - Select option to edit
    def editCommandSelectField(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()

        pair1 = query.data.split('/')[0]
        pair2 = query.data.split('/')[1]
        context.user_data['pair1'] = pair1
        context.user_data['pair2'] = pair2

        markup = ([InlineKeyboardButton(text='Editar precio', callback_data=1),
                   InlineKeyboardButton(text='Editar %pabilo', callback_data=2),
                   InlineKeyboardButton(text='Editar volumen', callback_data=3)])

        replyMarkup = InlineKeyboardMarkup([markup])

        context.bot.editMessageReplyMarkup(
            chat_id=query.message.chat_id, message_id=query.message.message_id, reply_markup=replyMarkup)

        return 2

    ## Edit command 2nd option - Introduce new value for selected field
    def editCommandIntroduceValue(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()

        option = query.data
        pair1 = context.user_data['pair1']
        pair2 = context.user_data['pair2']
        instances = self.getInstancesFromCSV()

        if option == '1':
            for i in range(len(instances)):
                if instances['pair1'][i] == pair1 and instances['pair2'][i] == pair2:
                    context.user_data['topPrice'] = instances['topPrice'][i]
                    context.user_data['volume'] = instances['volume'][i]
            query.edit_message_text(text=f"Ingresa el nuevo precio")
            return 3
        elif option == '2':
            for i in range(len(instances)):
                if instances['pair1'][i] == pair1 and instances['pair2'][i] == pair2:
                    context.user_data['price'] = instances['price'][i]
                    context.user_data['volume'] = instances['volume'][i]
            query.edit_message_text(text=f"Ingresa el nuevo %pabilo")
            return 4
        elif option == '3':
            for i in range(len(instances)):
                if instances['pair1'][i] == pair1 and instances['pair2'][i] == pair2:
                    context.user_data['price'] = instances['price'][i]
                    context.user_data['topPrice'] = instances['topPrice'][i]
            query.edit_message_text(text=f"Ingresa el nuevo volumen")
            return 5

    ## Edit command 3rd option - Edit price
    def editCommandPrice(self, update: Update, context: CallbackContext) -> None:
        message = update.message.text
        price = float(message)
        context.user_data['price'] = price

        if self.editCommandSaveInstance(update, context, 'price'):
            update.message.reply_text('Bot editado correctamente')
        else:
            update.message.reply_text('Hubo un error al editar el bot')
        return ConversationHandler.END

    ## Edit command 4th option - Edit %pabilo
    def editCommandCandlewick(self, update: Update, context: CallbackContext) -> None:
        message = update.message.text
        topPrice = float(message)
        context.user_data['topPrice'] = topPrice

        if self.editCommandSaveInstance(update, context, 'topPrice'):
            update.message.reply_text('Bot editado correctamente')
        else:
            update.message.reply_text('Hubo un error al editar el bot')
        return ConversationHandler.END
    

    ## Edit command 5th option - Edit volume
    def editCommandVolume(self, update: Update, context: CallbackContext) -> None:
        message = update.message.text
        volume = float(message)
        context.user_data['volume'] = volume

        if self.editCommandSaveInstance(update, context, 'volume'):
            update.message.reply_text('Bot editado correctamente')
        else:
            update.message.reply_text('Hubo un error al editar el bot')
        return ConversationHandler.END

    ## Save edited instance
    def editCommandSaveInstance(self, update: Update, context: CallbackContext, typeEdit) -> None:
        if typeEdit == 'price':
            price = context.user_data['price']
            topPrice = 'None'
            volume = 'None'
        elif typeEdit == 'topPrice':
            price = 'None'
            topPrice = context.user_data['topPrice']
            volume = 'None'
        elif typeEdit == 'volume':
            price = 'None'
            topPrice = 'None'
            volume = context.user_data['volume']

        pair1 = context.user_data['pair1']
        pair2 = context.user_data['pair2']
        pair = pair1 + '_' + pair2

        df = pd.DataFrame({'pair1': [pair1], 'pair2': [pair2], 'price': [
                          price], 'topPrice': [topPrice], 'volume': [volume]})

        try:
            df.to_csv(f'edit_{pair}.csv', index=False, header=False)
            return True
        except Exception as e:
            print(e)
            return False
    
    #* Various resources
    ## Cancel option
    def cancel(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id, text='Operación cancelada.')
        return ConversationHandler.END

    ## Get instances from CSV file instances.csv
    def getInstancesFromCSV(self):
        if os.path.exists('instances.csv'):
            columns = ['pair1', 'pair2', 'price',
                       'topPrice', 'volume', 'status']
            df = pd.read_csv('instances.csv', names=columns)
        else:
            df = pd.DataFrame()
        return df
