import telegramBot as tg
import logging
import resources as rs

logging.basicConfig(level=logging.DEBUG)
def main():
    logging.debug('Starting bot...')
    logging.warning('Bot started!')

    bot = tg.TelegramBot()
    bot.start()

if __name__ == '__main__':
    rs.sendTelegramMessage('Bot started!')
    main()