import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv

import text_messages
from exceptions import TelegramError

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


def check_tokens():
    """Проверка наличия всех токенов."""
    logging.info(text_messages.LOG_INFO_START_CHECK_TOKENS)
    none_tokens = []
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token_name in tokens:
        if tokens[token_name] is None:
            none_tokens.append(token_name)
            logging.critical(
                text_messages.LOG_CRITICAL_CHECK_TOKENS.format(
                    token_name=token_name
                )
            )
            if len(none_tokens) != 0:
                raise ValueError(
                    text_messages.NONE_TOKENS_ERROR_CHECK_TOKENS.format(
                        none_tokens=none_tokens
                    )
                )
    return tokens


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
        # Избавиться от логгирования здесь нельзя - требуют тесты.
        # Во всех остальных местах логгирование будет произведено
        # на "последнем рубеже" (кроме проверки токенов для
        # логгирования каждого пропущенного).
        raise TelegramError(
            text_messages.TELEGRAM_ERROR_SEND_MESSAGE.format(
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
        logging.info(
            text_messages.LOG_INFO_START_GET_API_ANSWER.format(
                params_request=params_request
            )
        )
    except requests.ConnectionError as error:
        raise ConnectionError(
            text_messages.CONNECTION_ERROR_GET_API_ANSWER.format(
                error=error
            )
        )
    except requests.RequestException as error:
        raise ConnectionError(
            text_messages.REQUEST_EXCEPTION_GET_API_ANSWER.format(
                error=error, params_request=params_request
            )
        )
    if response.status_code != 200:
        raise requests.HTTPError(
            text_messages.HTTP_ERROR_GET_API_ANSWER.format(
                status_code=response.status_code,
                params_request=params_request
            )
        )
    try:
        logging.debug(text_messages.LOG_DEBAG_GET_API_ANSWER)
        return response.json()
    except requests.JSONDecodeError:
        raise ValueError(text_messages.JSON_ERROR_GET_API_ANSWER)


def check_response(response):
    """Проверка ответа API."""
    logging.info(text_messages.LOG_INFO_START_CHECK_RESPONSE)
    if not isinstance(response, dict):
        raise TypeError(text_messages.NOT_DICT_ERROR_CHECK_RESPONSE.format(
            type=type(response)
        )
        )
    if 'homeworks' not in response:
        raise KeyError(text_messages.HOMEWORKS_KEY_ERROR_CHECK_RESPONSE)
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
        raise KeyError(text_messages.HOMEWORK_NAME_KEY_ERROR_PARSE_STATUS)
    homework.get('homework_name')
    if 'status' not in homework:
        raise KeyError(text_messages.STATUS_NAME_KEY_ERROR_PARSE_STATUS)
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise IndexError(
            text_messages.STATUS_ERROR_PARSE_STATUS.format(
                status=status
            )
        )
    logging.debug(text_messages.LOG_DEBAG_PARSE_STATUS)
    return (text_messages.MESSAGE_PARSE_STATUS.format(
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
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
                    logging.debug(text_messages.LOG_DEBUG_MAIN)
        except Exception as error:
            logging.exception(
                text_messages.LOG_EXCEPT_MAIN.format(
                    error=error
                )
            )
            # Надеюсь, что правильно поняла ваш комментарий, совсем
            # убрав пересылку об ошибках в телеграм, хоть она и была
            # в изначальном ТЗ. Я оставила бросок в строке 82.
            # В идеале, убрать лишнее логгирование в строке 71.
            # Если нужна пересылка в телеграм - добавлю ее здесь,
            # но уберу бросок в строке 82, а лишнее логгирование
            # перестанет быть лишним. Или оставлю бросок,
            # но добавлю ветвление здесь. Надеюсь, что правильно разобралась.
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
