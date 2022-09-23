import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания."
}

logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info("Начали отправку сообщения...")
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(f"Бот отправил сообщение: {message}")
    except telegram.error.TelegramError(message):
        error_message = "Из-за какой-то ошибки, " \
                        "бот не смог отправить сообщение"
        raise exceptions.MessageSendException(error_message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        logger.info("Начали запрос к API")
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ValueError as error:
        message = f"Ошибка в запросе к API Практикума {error}"
        raise ValueError(message)

    if response.status_code != HTTPStatus.OK:
        message = (f"Эндпоинт {ENDPOINT} недоступен!"
                   f"Код: {response.status_code}")
        raise exceptions.ErrorAPIException(message)

    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    # При запуске бота, применяя метод get(), тип объекта отображается
    # как 'dict',
    # !но в тестах этот метод не проходит и падает ошибка,
    # и этот метод там отображается как 'list'
    # print(type(response))
    # print(response)
    # homeworks_list = response.get("homeworks")
    homeworks_list = response["homeworks"]
    if "homeworks" and "current_date" not in response:
        message = "Нужных ключей нет в ответе API"
        raise exceptions.CheckResponseException(message)
    if not isinstance(homeworks_list, list):
        message = "Домашняя работа представлена не в виде списка!"
        raise exceptions.CheckResponseException(message)

    return homeworks_list


def parse_status(homework):
    """Извлекает статус из домашней работы."""
    if "homework_name" not in homework:
        message = "API вернул ответ без ключа homework_name"
        raise KeyError(message)
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if homework_status not in HOMEWORK_STATUSES:
        message = "Полученного статуса нет в словаре"
        raise KeyError(message)
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = "Отсутствует обязательная переменная окружения"
        logger.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # from time import mktime
    # from datetime import datetime, timedelta
    # days_60 = datetime.today() - timedelta(days=90)
    # current_timestamp = int(mktime(days_60.timetuple()))
    current_timestamp = int(time.time())

    while True:
        try:
            response_api = get_api_answer(current_timestamp)
            homeworks_list = check_response(response_api)
            logger.info("Получен список с домашками")
            if homeworks_list:
                message = parse_status(homeworks_list[0])
                send_message(bot, message)
            else:
                logger.info("Домашки не обнаружены")
            current_timestamp = response_api["current_date"]

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
