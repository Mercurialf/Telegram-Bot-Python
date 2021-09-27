"""Простой телеграм-бот, который парсит информацию о погоде и валюте, отвечает на простые сообщения
используя заранее заготовленные списки, ведет лог."""
import logging
import random
import set  # Импорт собственных списков.
import sqlite3

# Библиотека для запросов и работы с html.
from bs4 import BeautifulSoup
import requests

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

__version__ = '0.1'

"""Создание логов"""
logging_file = 'telegram_bot.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s : %(levelname)s : %(message)s',
    filename=logging_file,
    filemode='w',
)
logging.debug('Version TelegramBot -- {0}'.format(__version__))

"""Инициализация бота"""
API_TOKEN = '#'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Я бот, Привет! Я умею узнавать погоду, например 'Погода Киев'. Или конвертировать USD "
                        "в PLN и обратно, например '100 USD'. Или ты можешь получить случайный ответ на вопрос:"
                        " Да или нет? Так же ты можешь получить невероятно ценный совет воспользовавшись"
                        " командой /advice.")
    logging.info('Using /start or /help')


@dp.message_handler(commands=['advice'])
async def send_wisdom(message: types.Message):
    # Выбор случайного элемента из списка с помощью random.choice().
    await message.reply(random.choice(set.advice_list))
    logging.info('Using /advice')


"""Парсинг курса"""
URL = 'https://forexbrest.info/kurs-nacbank/poland/'
HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
           'accept': '*/*'}


# Функция для добавляения дополнительных параметров к url.
def get_html(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    return r


# Функция получения конкретного заранее известного элемента с html страницы.
def get_content(html):
    # Второй параметр - тип документа с которым работаем.
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all(class_='kurs')

    table = 0
    for item in items:
        table = item.find(class_='odd').get_text(strip=True).replace('Доллар США1 USD', '')
    return table


# Основная функция.
def parse():
    html = get_html(URL)
    # Проверяем доступность страницы.
    if html.status_code == 200:
        # Получаем контент с страницы, а именно переменную с текущим курсом.
        values = get_content(html.text)
        return values
    # Если что-то пошло не так, выводим сообщение в консоль.
    else:
        print('Ошибка получения информации с сайта.')


def calculation_currency(usd, pln, choice):
    c = float(usd)
    y = float(pln)
    x = 0

    if choice == 1:
        x = c * y
        # Сокращяем кол-во знаков после запятой с помощью "%.2f".
        x = "%.2f" % x
        str(x)
    elif choice == 2:
        x = y / c
        x = "%.2f" % x
        str(x)

    return x


'''Парсинг прогноза погоды в формате мин/макс + короткое описание с сайта.
Основная функция check_weather получает название города от пользователя.'''


def check_weather(location):
    # С помощью функции lower(), переводим слово в нижний регистр.
    requests_weather = requests.get('https://sinoptik.ua/погода-{0}/'.format(location.lower()))
    html = BeautifulSoup(requests_weather.content, 'html.parser')

    # Перебераем список элеменов на сайте.
    for element in html.select('#content'):
        t_min = element.select('.temperature .min')[0].text
        t_max = element.select('.temperature .max')[0].text
        text = element.select('.wDescription .description')[0].text
        return t_min.capitalize() + ', ' + t_max.capitalize() + '\n' + text.lstrip()


"""Функция с помощью которой проверяем сообщения на совпадение
с заранее заготовленными списками из файла 'set.py'."""


def check_set(message, default_set):
    for words in default_set:
        if str(message) == words:
            return True
        # Возвращает индекс подстроки в строке. Если подстрока не найдена, возвращается число -1.
        elif message.find(words) != -1:
            return True


# Случайный ответ пользователю.
def random_choice():
    if random.randint(0, 1) == 1:
        return 'Да'
    else:
        return 'Нет'


# Основная функция проверки сообщений от пользователя.
@dp.message_handler(content_types=['text'])
async def get_text_messages(message: types.Message):
    # Проверяем полученное текстовое сообщение от пользователя.
    if check_set(message.text, set.main_list):
        await message.answer(random.choice(set.main_answer_list))
        logging.info('Using "set.main_list"')

    # Да или нет, случайный ответ
    if check_set(message.text, set.rand_list):
        await message.answer(random_choice())
        logging.info('Using "random_choice()"')

    """
    Вызов функция с помощью которой узнаем погоду, используя список из 'set'.
    """
    if check_set(message.text, set.weather_list):
        # Используем функцию .split() чтобы разбить сообщение на список.
        my_list = message.text.split()
        await message.answer(check_weather(my_list[1]))
        logging.info('Using "weather_list"')

    """"
    Вызов функция конвертации валют.
    """
    if check_set(message.text, set.currency_list_usd):
        user_currency = message.text.split()
        await message.answer('PLN - {0}'.format(calculation_currency(parse(), user_currency[0], 1)))
        logging.info('Using PLN currency')
    if check_set(message.text, set.currency_list_pln):
        user_currency = message.text.split()
        await message.answer('USD - {0}'.format(calculation_currency(parse(), user_currency[0], 2)))
        logging.info('Using USD currency')

"""SQLite3"""
conn = sqlite3.connect('list.db')
cur = conn.cursor()


def check_list(string, data_list):
    for words in data_list:
        x = str(words)
        y = x.replace("('", '')
        z = y.replace("',)", '')

        if z == string:
            print('True')
            return True


# Функция постоянной проверки наличия сообщений.
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
