import configparser
import requests

# Читаем конфигурационный файл
config = configparser.ConfigParser()
config.read("settings.ini", encoding="utf-8-sig")

# Получаем ключ API и Folder ID
YANDEX_API_KEY = config.get("Tokens", "YANDEX_API_KEY", fallback=None)
FOLDER_ID = config.get("Tokens", "FOLDER_ID", fallback=None)

# Тестовое слово для перевода
TEST_WORD = "test"

# Формируем запрос к API Яндекса
url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
headers = {
    "Authorization": f"Api-Key {YANDEX_API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "targetLanguageCode": "ru",
    "texts": [TEST_WORD],
    "folderId": FOLDER_ID
}

# Отправляем тестовый запрос
print(f"🔍 Проверяем API-ключ: {YANDEX_API_KEY[:5]}... (скрыто)")
print(f"🔍 Проверяем Folder ID: {FOLDER_ID}")

try:
    response = requests.post(url, json=data, headers=headers, timeout=5)
    if response.status_code == 200:
        translation = response.json().get("translations", [{}])[0].get("text", "")
        print(f"API работает! Перевод слова '{TEST_WORD}': {translation}")
    else:
        print(f"Ошибка API: {response.status_code} - {response.text}")
except requests.exceptions.Timeout:
    print("Время ожидания API истекло! Проверь подключение к интернету.")
except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе к API: {e}")
