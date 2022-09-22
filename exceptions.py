class ResponseAPIException(Exception):
    """Возникла ошибка при попытке поключиться к API"""

    pass


class ErrorAPIException(Exception):
    """Возникла ошибка в работе программы"""

    pass


class CheckResponseException(Exception):
    """Был получен неверный ответ от API"""

    pass


class TokenException(Exception):
    """Потеряна одна из переменных окружения"""

    pass


class HomeworkStatusException(Exception):
    """У домашней работы не установлен статус проверки"""

    pass
