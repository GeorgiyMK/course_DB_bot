import psycopg2
import requests
import random
import time
import configparser
from sqlalchemy import create_engine, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base

# Обращаемся к файлу с данными
config = configparser.ConfigParser()
config.read('settings.ini')

# берём необходимые для работы данные из файла settings.ini
DB_NAME = config['Tokens']['DB_NAME']
DB_USER = config['Tokens']['DB_USER']
DB_PASSWORD = config['Tokens']['DB_PASSWORD']
DB_HOST = config['Tokens']['DB_HOST']
DB_PORT = config['Tokens']['DB_PORT']

# Создание подключения к БД
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Создаём таблицу
class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True, autoincrement=True)
    english_word = Column(String(100), unique=True, nullable=False)
    russian_translation = Column(String(100), nullable=False)

    __table_args__ = (UniqueConstraint("english_word", name="uq_english_word"),)


# Функция для получения случайного английского слова и его перевода
def get_random_word():
    try:
        response = requests.get("https://random-word-api.herokuapp.com/word?number=1")
        if response.status_code == 200:
            word = response.json()[0]
            translate_response = requests.get(f"https://api.mymemory.translated.net/get?q={word}&langpair=en|ru")
            if translate_response.status_code == 200:
                translation = translate_response.json()["responseData"]["translatedText"]
                return word, translation
    except Exception as e:
        print(f"Ошибка при получении слова: {e}")
    return None, None


# Функция для добавления слов в базу данных
def insert_words(n=1000):
    session = SessionLocal()
    for _ in range(n):
        word, translation = get_random_word()
        if word and translation:
            try:
                existing_word = session.query(Word).filter_by(english_word=word).first()
                if not existing_word:
                    new_word = Word(english_word=word, russian_translation=translation)
                    session.add(new_word)
                    session.commit()
                    print(f"Добавлено: {word} - {translation}")
            except Exception as e:
                session.rollback()
                print(f"Ошибка при добавлении слова {word}: {e}")
        time.sleep(1)  # Задержка, чтобы избежать блокировки API
    session.close()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    insert_words(1000)