import json
import logging
import os
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
import requests
import telegram

from exceptions import ParseStatusError, APIrequestError, TokenMissingError

load_dotenv()

logging.basicConfig(
    filename='main.log',
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token, value in tokens.items():
        if not value:
            message = f'отсутствует обязательная переменная окружения: {token}'
            logger.critical(message)
            raise TokenMissingError(message)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Бот отправил сообщение.')
    except telegram.error.TelegramError:
        logger.error('Не удалось отправить сообщение в ТГ')


def get_api_answer(timestamp):
    """Запрос к основному API.

    Возвращает список проверенных домашних заданий, преобразуя ответ
    в формате JSON в типы данных python. Согласно документации API,
    для запроса необходим параметр from_date. В ответе по ключу
    "homeworks" будет содержаться список домашних работ, статус которых
    изменился за период от from_date до настоящего момента. Список будет
    пуст, если за выбранный интервал времени ни у одной из домашних работ
    не появился новый статус.
    """
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException:
        raise APIrequestError('Ошибка модуля requests')
    if response.status_code != HTTPStatus.OK:
        message = (f'Ошибка при запросе к API, '
                   f'статус ответа: {response.status_code}')
        raise APIrequestError(message)
    try:
        response = response.json()
    except json.decoder.JSONDecodeError:
        raise APIrequestError('Ответ API не в JSON формате')
    return response


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    message = 'ответ API не соответствует документации'
    if not isinstance(response, dict):
        raise TypeError(message)
    if 'homeworks' not in response:
        raise TypeError(message)
    if 'current_date' not in response:
        raise TypeError(message)
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(message)
    if not isinstance(response.get('current_date'), int):
        raise TypeError(message)


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    if 'homework_name' not in homework:
        raise ParseStatusError('нет ключа homework_name')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logger.error('неожиданный статус домашней работы')
        raise ParseStatusError('неожиданный статус домашней работы')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 7 * 24 * 60 * 60  # задаём интервал (неделя)
    message_last_status = ''
    errors = []
    while True:
        try:
            answer = get_api_answer(timestamp)
            check_response(answer)
            homework_list = answer.get('homeworks')
            if not homework_list:
                logger.debug('Список домашек пуст, изменений нет.')
            else:
                for homework in homework_list:
                    info = parse_status(homework)
                    if message_last_status != info:
                        send_message(bot, info)
                    message_last_status = info
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if error not in errors:
                errors.append(error)
        finally:
            timestamp = answer.get('current_date')
            for error in errors:
                bot.send_message(
                    TELEGRAM_CHAT_ID,
                    f'Хьюстон, у нас проблемы: {error}'
                )
            errors = []
            logger.debug('Спим 600 секунд')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
