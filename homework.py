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
    timestamp = current_timestamp
    params = {"from_date": timestamp}
    try:
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
    try:
        homeworks_list = response["homeworks"]
    except KeyError as error:
        message = f"Ошибка доступа по ключу: {error}"
        raise exceptions.CheckResponseException(message)
    if "homeworks" and "current_date" not in response:
        message = "Нужных ключей нет в ответе API"
        raise exceptions.CheckResponseException(message)
    if not isinstance(homeworks_list, list):
        message = "Домашняя работа представлена не в виде списка!"
        raise exceptions.CheckResponseException(message)
    return homeworks_list


def parse_status(homework):
    """Извлекает статус из домашней работы."""
    if "homework_name" in homework:
        homework_name = homework.get("homework_name")
    else:
        message = "API вернул ответ без ключа homework_name"
        raise KeyError(message)
    homework_status = homework.get("status")
    if homework_status not in HOMEWORK_STATUSES:
        message = "Полученного статуса нет в словаре"
        raise KeyError(message)
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        message = "API вернул неизвестный статус"
        raise exceptions.HomeworkStatusException(message)

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
    # days_60 = datetime.today() - timedelta(days=60)
    # current_timestamp = int(mktime(days_60.timetuple()))
    current_timestamp = int(time.time())
    update_time = []

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_list = check_response(response)

            for homework in homeworks_list:
                date_updated = homework.get("date_updated")
                if date_updated not in update_time:
                    update_time.append(date_updated)
                    message = parse_status(homework)
                    send_message(bot, message)

            current_timestamp = int(time.time())

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
