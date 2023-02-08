import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

import text_messages
from exceptions import ApiAnswerError

load_dotenv()

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

TOKENS = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID',
]


def check_tokens():
    """Проверка наличия всех токенов."""
    logging.info(text_messages.LOG_INFO_START_CHECK_TOKENS)
    none_tokens = [token_name for token_name in TOKENS if globals()[token_name] is None]
    if len(none_tokens) != 0:
        logging.critical(
            text_messages.LOG_CRITICAL_CHECK_TOKENS.format(
                none_tokens=none_tokens
            )
        )
        raise ValueError(
            text_messages.NONE_TOKENS_ERROR_CHECK_TOKENS.format(
                none_tokens=none_tokens
            )
        )


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    try:
        logging.info(
            text_messages.LOG_INFO_START_SEND_MESSAGE.format(
                message=message
            )
        )
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(
            text_messages.LOG_DEBAG_SEND_MESSAGE.format(
                message=message
            )
        )
    except telegram.error.TelegramError as error:
        logging.exception(
            text_messages.LOG_EXCEPT_SEND_MESSAGE.format(
                message=message,
                error=error
            )
        )


def get_api_answer(timestamp):
    """Запрос к API."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        response = requests.get(**params_request)
    except requests.RequestException as error:
        raise ConnectionError(
            text_messages.REQUEST_EXCEPTION_GET_API_ANSWER.format(
                error=error, params_request=params_request
            )
        )
    if response.status_code != 200:
        raise ApiAnswerError(
            text_messages.HTTP_NOT_OK_ERROR_GET_API_ANSWER.format(
                status_code=response.status_code,
                params_request=params_request
            )
        )
    if 'error' in response.json():
        raise ApiAnswerError(
            text_messages.RESPONSE_ERROR_GET_API_MESSAGE.format(
                error=response.json()['error']
            )
        )
    if 'code' in response.json():
        raise ApiAnswerError(
            text_messages.RESPONSE_ERROR_CODE_GET_API_MESSAGE.format(
                code=response.json()['code']
            )
        )
    logging.debug(text_messages.LOG_DEBAG_GET_API_ANSWER)
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    logging.info(text_messages.LOG_INFO_START_CHECK_RESPONSE)
    if not isinstance(response, dict):
        raise TypeError(
            text_messages.NOT_DICT_ERROR_CHECK_RESPONSE.format(
                type=type(response)
            )
        )
    if 'homeworks' not in response:
        raise KeyError(
            text_messages.HOMEWORKS_KEY_ERROR_CHECK_RESPONSE
        )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            text_messages.NOT_LIST_ERROR_CHECK_RESPONSE.format(
                type=type(homeworks)
            )
        )
    logging.debug(text_messages.LOG_DEBAG_CHECK_RESPONSE)
    return homeworks


def parse_status(homework):
    """Извлечение информации о статусе работы."""
    if 'homework_name' not in homework:
        raise KeyError(
            text_messages.HOMEWORK_NAME_KEY_ERROR_PARSE_STATUS
        )
    if 'status' not in homework:
        raise KeyError(
            text_messages.STATUS_NAME_KEY_ERROR_PARSE_STATUS
        )
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            text_messages.STATUS_ERROR_PARSE_STATUS.format(
                status=status
            )
        )
    logging.debug(text_messages.LOG_DEBAG_PARSE_STATUS)
    return (
        text_messages.MESSAGE_PARSE_STATUS.format(
            homework_name=homework.get('homework_name'),
            verdict=HOMEWORK_VERDICTS[status]
        )
    )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    logging.info(text_messages.LOG_INFO_MAIN)
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                continue
            message = parse_status(homeworks[0])
            if last_message != message:
                send_message(bot, message)
                last_message = message
                logging.debug(text_messages.LOG_DEBUG_MAIN)
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = text_messages.MAIN_ERROR_MESSAGE.format(
                error=error
            )
            logging.exception(
                text_messages.LOG_EXCEPT_MAIN.format(
                    error=error
                )
            )
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(
                filename=__file__ + '.log', mode='w', encoding='UTF-8'),
            logging.StreamHandler(stream=sys.stdout)
        ],
        format='%(asctime)s, %(levelname)s, %(funcName)s, '
               '%(lineno)s, %(message)s',
    )
    main()
