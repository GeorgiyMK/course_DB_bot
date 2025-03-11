import telebot
import configparser

# Читаем конфигурационный файл
config = configparser.ConfigParser()
config.read("settings.ini", encoding="utf-8-sig")

# Параметры подключения к боту
TOKEN = config["Tokens"]["TOKEN"]


bot = telebot.TeleBot(TOKEN)

# Декоратор хендлер, учит бот реагировать на что-либо, в данном случае на команду start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 'Привет, я английскому обучатель!')

@bot.message_handler(commands=['help'])
def answer_to_help(message):
    bot.reply_to(message, 'Помоги себе сам!')

@bot.message_handler(func=lambda message: True)
def answer_to_any_message(message):
    bot.reply_to(message, 'Не дохера ли хочешь?')


if __name__ == '__main__':
    print('Bot starts!')
    # Ожидание сообщений от пользователя
    bot.polling()