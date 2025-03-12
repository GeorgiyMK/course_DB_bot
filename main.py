import random
import telebot
from telebot import types
import configparser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from sqlalchemy import create_engine, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from telebot.states import StatesGroup, State
from create_DBdict import engine, Word

# Читаем конфигурационный файл
config = configparser.ConfigParser()
config.read("settings.ini", encoding="utf-8-sig")

# Параметры подключения к боту
TOKEN = config["Tokens"]["TOKEN"]

bot = telebot.TeleBot(TOKEN)
class Command:
    ADD_WORD = '💡 Добавить слово 💡'
    DELETE_WORD = '❌ Удалить слово ❌'
    NEXT = '🤷‍♂️ Пропустить слово 🤷‍♂️'

class MyStates(StatesGroup):
    target_word = State()
    russian_word = State()
    wrong_words = State()

Session = sessionmaker(bind=engine)

# Декоратор хендлер, учит бот реагировать на что-либо, в данном случае на команду start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 'Привет, я английскому обучатель! Знаю три команды /start , /help и /start_studying')

@bot.message_handler(commands=['start_studying'])
def studying(message):
    session = Session()
    # Получаем случайное слово из БД
    word_pair = session.query(Word).order_by(func.random()).first()
    if not word_pair:
        bot.reply_to(message, "⚠️ Ошибка: База данных пуста! ⚠️")
        return
    russian_word = word_pair.russian_translation
    target_word = word_pair.english_word

    # Получаем три случайных неправильных слова
    wrong_words = (
        session.query(Word.english_word)
        .filter(Word.english_word != target_word) # Проверяем, что бы не было совпадений с верным словом
        .order_by(func.random())
        .limit(3)
        .all()
    )

    # Преобразуем в список строк
    wrong_words = [w[0] for w in wrong_words]

    # Делаем кнопки
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    target_word_btn = types.KeyboardButton(target_word)
    wrong_words_btns = [types.KeyboardButton(word) for word in wrong_words]

    # Перемешиваем кнопки
    buttons = [target_word_btn] + wrong_words_btns
    random.shuffle(buttons)

    # Добавляем доп. кнопки
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    next_word_btn = types.KeyboardButton(Command.NEXT)

    # Добавляем кнопки в разметку
    markup.add(*buttons,add_word_btn, delete_word_btn, next_word_btn)

    # Отправляем сообщение с вопросом
    bot.send_message(
        message.chat.id,
        f"🔹 Как перевести: *{russian_word}*?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['russian_word'] = russian_word
        data['wrong_words'] = wrong_words

    session.close()

@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_answer(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        print(f"Retrieved state: {data}")  # Логирование данных

        if 'target_word' not in data:
            bot.send_message(message.chat.id, "⚠️ Ошибка: Отправьте команду /start_studying, прежде чем отвечать!")
            return

        target_word = data['target_word']

    if message.text == target_word:
        bot.send_message(message.chat.id, '🔥 Слово определено верно! 🔥')
        studying(message)  # Следующее слово
    else:
        bot.send_message(message.chat.id, '❌ Не верно! Попробуй ещё ❌')

@bot.message_handler(commands=['help'])
def answer_to_help(message):
    bot.reply_to(message, 'Помоги себе сам!')

if __name__ == '__main__':
    print('Bot starts!')
    # Ожидание сообщений от пользователя
    bot.polling()