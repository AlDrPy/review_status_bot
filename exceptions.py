class APIresponseTypeError(Exception):
    """Исключение для недокуентированного ответа API."""

    pass


class APIrequestError(Exception):
    """Ошибка при запросе к API."""

    pass


class TokenMissingError(Exception):
    """Отсутствует токен или другая переменная окружения."""

    pass


class ParseStatusError(Exception):
    """Ошибка при получении статуса домашней работы."""

    pass
