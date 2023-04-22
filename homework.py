import os
import sys
import time
import requests
import logging
import telegram
from pprint import pprint
from exceptions import *

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
TELEGRAM_CHAT_ID = 1100385471

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
        'токен Практикума': PRACTICUM_TOKEN,
        'токен телеги': TELEGRAM_TOKEN,
        'номер чата в телеге': TELEGRAM_CHAT_ID
    }
    for token, value in tokens.items():
        if not value:
            message = f'отсутствует переменная окружения: {token}'
            logger.critical(message)
            raise TokenMissingError(message)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    pass


def get_api_answer(timestamp):
    """Запрос к основному API.

    Возвращает список проверенных домашних заданий в формате JSON,
    преобразованном в типы данных питона.
    """
    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params={'from_date': timestamp}
    )
    if response.status_code != 200:
        raise APIrequestError(
            'Ошибка при запросе к API, статус ответа: ',
            response.status_code)
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    check_list = [
        isinstance(response, dict),
        response.get('homeworks') is not None,
        response.get('current_date') is not None,
    ]
    for i in check_list:
        if not i:
            raise APIresponseTypeError(
                'ответ API не соответствует документации')


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    print(f'Изменился статус проверки работы "{homework_name}". \n{verdict}\n')
    #   return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    # bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # timestamp = int(time.time()) - 30 * 24 * 60 * 60  # месяц назад
    timestamp = 0
    while True:
        try:
            answer = get_api_answer(timestamp)
            check_response(answer)
            homework_list = answer.get('homeworks')
            for homework in homework_list:
                parse_status(homework)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
        finally:
            timestamp = answer.get('current_date')
            print('Спим 600 секунд')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
