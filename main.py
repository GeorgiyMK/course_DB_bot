import random
import telebot
from telebot import types
import configparser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from sqlalchemy import create_engine, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from telebot.states import StatesGroup, State
from create_DBdict import engine, Word, User as DBUser
from telebot.storage import StateMemoryStorage

storage = StateMemoryStorage()


# Читаем конфигурационный файл
config = configparser.ConfigParser()
config.read("settings.ini", encoding="utf-8-sig")

# Параметры подключения к боту
TOKEN = config["Tokens"]["TOKEN"]

bot = telebot.TeleBot(TOKEN, state_storage=storage)
class Command:
    ADD_WORD = '💡 Добавить слово 💡'
    DELETE_WORD = '❌ Удалить слово ❌'
    NEXT = '🤷‍♂️ Пропустить слово 🤷‍'

class MyStates(StatesGroup):
    target_word = State()
    russian_word = State()
    wrong_words = State()
    waiting_for_english_word = State()
    waiting_for_translation = State()
    waiting_for_username = State()

Session = sessionmaker(bind=engine)

# Декоратор хендлер, учит бот реагировать на что-либо, в данном случае на команду start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    session = Session()
    bot.reply_to(message, 'Привет, я английскому обучатель! Знаю три команды /start , /help и /start_studying')
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в БД
    user = session.query(DBUser).filter(DBUser.user_id == user_id).first()

    if not user:
        # **Регистрируем нового пользователя**
        new_user = DBUser(user_id=user_id, username=f"user_{user_id}")
        session.add(new_user)
        session.commit()

        # **Копируем слова из общей базы в персональную БД пользователя**
        common_words = session.query(Word).filter(Word.user_id == None).all()
        if common_words:
            for word in common_words:
                new_word = Word(
                    english_word=word.english_word,
                    russian_translation=word.russian_translation,
                    user_id=user_id
                )
                session.add(new_word)
            session.commit()
            bot.send_message(message.chat.id, "📚 Вам доступна базовая база слов! Введите /start_studying.")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка: Общая база слов пуста. Обратитесь к администратору.")

    else:
        bot.send_message(message.chat.id, "🔹 Добро пожаловать обратно! Для продолжения обучения нажмите /start_studying")

    session.close()

@bot.message_handler(state=MyStates.waiting_for_username, content_types=['text'])
def save_username(message):
    session = Session()
    user_id = message.from_user.id
    username = message.text.strip()

    existing_user = session.query(DBUser).filter(DBUser.user_id == user_id).first()
    if not existing_user:
        new_user = DBUser(user_id=user_id, username=username)
        session.add(new_user)
        session.commit()

        bot.send_message(message.chat.id, f"👋 {username}, вы добавлены в систему!")

        # Копируем начальную БД
        common_words = session.query(Word).filter(Word.user_id == None).all()
        if common_words:
            words_to_add = [
                Word(english_word=w.english_word, russian_translation=w.russian_translation, user_id=user_id)
                for w in common_words
            ]
            if words_to_add:
                session.bulk_save_objects(words_to_add)
                session.commit()
                bot.send_message(message.chat.id, "📚 Вам доступна базовая база слов! Введите /start_studying.")
            else:
                bot.send_message(message.chat.id, "⚠️ Внимание: Общая база слов пуста. Обратитесь к администратору.")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка: Общая база слов пуста. Обратитесь к администратору.")

    else:
        bot.send_message(message.chat.id, f"🔹 Добро пожаловать обратно, {existing_user.username}!")

    session.close()
    bot.delete_state(user_id, message.chat.id)

# Запускаем функцию пропустить слово при срабатывании команды NEXT
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def skip_word(message):
    studying(message)

# Запускаем функцию удаления слова из персональной БД пользователя при срабатывании команды DELETE_WORD
@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    session = Session()
    user_id = message.from_user.id  # Получаем user_id из Telegram

    with bot.retrieve_data(user_id, message.chat.id) as data:
        if 'target_word' not in data:
            bot.send_message(message.chat.id, "⚠️ Ошибка: Сначала начните изучение слов.")
            return

        target_word = data['target_word']

    word_entry = session.query(Word).filter(Word.english_word == target_word, Word.user_id == user_id).first()

    if word_entry:
        session.delete(word_entry)
        session.commit()
        bot.send_message(message.chat.id, f"✅ Слово *{target_word}* удалено из вашей базы!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Это слово не найдено в вашей базе.")

    session.close()
    studying(message)

# Запускаем функцию добавления слова в персональную БД пользователя при срабатывании команды ADD_WORD
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def request_english_word(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    bot.set_state(user_id, MyStates.waiting_for_english_word, chat_id)
    bot.add_data(user_id, chat_id, {"new_english_word": None})  # Устанавливаем заготовку
    bot.send_message(chat_id, "✍ Введите английское слово:")

@bot.message_handler(state=MyStates.waiting_for_english_word, content_types=['text'])
def request_translation(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    with bot.retrieve_data(user_id, chat_id) as data:
        data.update({'new_english_word': message.text.strip().lower()})

    bot.set_state(user_id, MyStates.waiting_for_translation, chat_id)
    bot.send_message(chat_id, "🔤 Теперь введите перевод:")

@bot.message_handler(state=MyStates.waiting_for_translation, content_types=['text'])
def save_word_to_db(message):
    session = Session()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Используем контекстный менеджер
    with bot.retrieve_data(user_id, chat_id) as data:
        if 'new_english_word' not in data:  # Проверка теперь работает
            bot.send_message(chat_id, "⚠️ Ошибка! Попробуйте снова добавить слово.")
            return

        english_word = data['new_english_word']
        russian_translation = message.text.strip().lower()

    # Проверяем, есть ли слово в базе пользователя
    existing_word = session.query(Word).filter(Word.english_word == english_word, Word.user_id == user_id).first()
    if existing_word:
        bot.send_message(chat_id, f"⚠️ Слово *{english_word}* уже есть в вашей базе.", parse_mode="Markdown")
    else:
        new_word = Word(english_word=english_word, russian_translation=russian_translation, user_id=user_id)
        session.add(new_word)
        session.commit()
        bot.send_message(chat_id, f"✅ Слово *{english_word}* → *{russian_translation}* добавлено!", parse_mode="Markdown")

    session.close()
    bot.delete_state(user_id, chat_id)  # Очищаем состояние
    studying(message)

@bot.message_handler(commands=['start_studying'])
def studying(message):
    session = Session()
    user_id = message.from_user.id

    words_count = session.query(Word).filter(Word.user_id == user_id).count()
    if words_count == 0:
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка: У вас нет слов в базе! Добавьте слова командой '💡 Добавить слово 💡' или обратитесь к администратору."
        )
        session.close()
        return

    word_pair = session.query(Word).filter(Word.user_id == user_id).order_by(func.random()).first()
    if not word_pair:
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка: База данных пуста! Попробуйте добавить слово командой '💡 Добавить слово 💡'."
        )
        session.close()
        return

    russian_word = word_pair.russian_translation
    target_word = word_pair.english_word

    wrong_words = session.query(Word.english_word).filter(
        Word.user_id == user_id, Word.english_word != target_word
    ).order_by(func.random()).limit(3).all()

    wrong_words = [w[0] for w in wrong_words]

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(target_word)] + [types.KeyboardButton(word) for word in wrong_words]
    random.shuffle(buttons)
    markup.add(
        *buttons,
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD),
        types.KeyboardButton(Command.NEXT)
    )

    bot.send_message(
        message.chat.id,
        f"🔹 Как перевести: *{russian_word}*?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

    bot.set_state(user_id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(user_id, message.chat.id) as data:
        data.update({'target_word': target_word, 'russian_word': russian_word, 'wrong_words': wrong_words})

    session.close()

@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_answer_or_handle_state(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    state = bot.get_state(user_id, chat_id)

    if state == MyStates.waiting_for_english_word.name:
        request_translation(message)  # Переход к вводу перевода
        return
    elif state == MyStates.waiting_for_translation.name:
        save_word_to_db(message)  # Сохранение нового слова
        return

    # Если не в режиме добавления, проверяем как ответ в тесте
    with bot.retrieve_data(user_id, chat_id) as data:
        if not data or 'target_word' not in data:
            bot.send_message(chat_id, "⚠️ Ошибка: Отправьте команду /start_studying, прежде чем отвечать!")
            return

        target_word = data['target_word']

    if message.text.strip().lower() == target_word.lower():
        bot.send_message(chat_id, '🔥 Слово определено верно! 🔥')
        studying(message)  # Следующее слово
    else:
        bot.send_message(chat_id, '❌ Не верно! Попробуй ещё ❌')

@bot.message_handler(commands=['help'])
def answer_to_help(message):
    bot.reply_to(message, 'Помоги себе сам!')

if __name__ == '__main__':
    print('Bot starts!')
    # Ожидание сообщений от пользователя
    bot.polling()