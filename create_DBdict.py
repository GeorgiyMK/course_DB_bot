import configparser
import requests
import random
import time
import PyPDF2
from sqlalchemy import create_engine, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base

# Читаем конфигурационный файл
config = configparser.ConfigParser()
config.read("settings.ini", encoding="utf-8-sig")

# Параметры подключения к базе данных
DB_NAME = config["Tokens"]["DB_NAME"]
DB_USER = config["Tokens"]["DB_USER"]
DB_PASSWORD = config["Tokens"]["DB_PASSWORD"]
DB_HOST = config["Tokens"]["DB_HOST"]
DB_PORT = int(config["Tokens"]["DB_PORT"])  # Преобразуем в число
YANDEX_API_KEY = config['Tokens']['YANDEX_API_KEY']
FOLDER_ID = config['Tokens']['FOLDER_ID']

# Подключение к базе данных
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Создаём таблицу
class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True, autoincrement=True)
    english_word = Column(String(15), unique=True, nullable=False)
    russian_translation = Column(String(15), nullable=False)

    __table_args__ = (UniqueConstraint("english_word", name="uq_english_word"),)


# Функция для загрузки слов из PDF-файла
def extract_words_from_pdf(pdf_path, num_words=300):
    words = set()
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    words.update(text.split())
    except Exception as e:
        print(f"⚠️ Ошибка при чтении PDF: {e}")

    # Убираем знаки препинания и цифры, оставляем только слова
    words = {word.strip(".,!?()[]{}<>:;\"'").lower() for word in words if word.isalpha()}
    return random.sample(list(words), min(len(words), num_words))


# Функция для перевода слова с Yandex API
def translate_word(word):
    url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "targetLanguageCode": "ru",
        "texts": [word],
        "folderId": FOLDER_ID
    }
    print(f"🔍 Переводим: {word}")

    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        if response.status_code == 200:
            translation = response.json().get("translations", [{}])[0].get("text", "")
            return translation if translation.lower() != word.lower() else None
        else:
            print(f"Ошибка API {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
    return None


# Функция для добавления слов в базу данных
def insert_words(pdf_path):
    words = extract_words_from_pdf(pdf_path, num_words=300)
    if not words:
        print("Ошибка: не удалось загрузить слова из PDF.")
        return

    with SessionLocal() as session:
        for word in words:
            translation = translate_word(word)
            if translation:
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
            time.sleep(0.03)  # Задержка для API


if __name__ == "__main__":
    Base.metadata.drop_all(engine) # Удаляем табл если есть
    Base.metadata.create_all(engine)  # Создаём таблицу, если её нет
    insert_words("Treasure_Island.pdf")
