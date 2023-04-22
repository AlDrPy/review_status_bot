import os
import sys
import time
import requests
import logging
import telegram
from exceptions import ParseStatusError, APIrequestError, TokenMissingError

from dotenv import load_dotenv

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
TELEGRAM_TOKEN = os.getenv('HOMEWORK_BOT_TOKEN')
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

    Возвращает список проверенных домашних заданий в формате JSON,
    преобразованном в типы данных питона.
    """
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException:
        logger.error('ошибка модуля Requests')
    if response.status_code != 200:
        message = (f'Ошибка при запросе к API, '
                   f'статус ответа: {response.status_code}')
        logger.error(message)
        raise APIrequestError(message)
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    message = 'ответ API не соответствует документации'
    if not isinstance(response, dict):
        logger.error(message)
        raise TypeError(message)
    if 'homeworks' not in response.keys():
        logger.error(message)
        raise TypeError(message)
    if 'current_date' not in response.keys():
        logger.error(message)
        raise TypeError(message)
    if not isinstance(response.get('homeworks'), list):
        logger.error(message)
        raise TypeError(message)
    if not isinstance(response.get('current_date'), int):
        logger.error(message)
        raise TypeError(message)


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    if 'homework_name' not in homework:
        raise ParseStatusError('нет ключа homework_name')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        logger.error('неожиданный статус домашней работы')
        raise ParseStatusError('неожиданный статус домашней работы')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 7 * 24 * 60 * 60  # неделю назад
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
                    send_message(bot, info)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
        finally:
            timestamp = answer.get('current_date')
            logger.debug('Спим 600 секунд')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
