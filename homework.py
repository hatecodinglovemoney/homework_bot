import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv

from exceptions import WrongGetApiAnswer, TelegramError, \
    WrongCheckResponse, WrongParseStatus

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
    logging.info('Проверка наличия всех токенов.')
    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    for token in tokens:
        if token is None:
            logging.critical(
                f'Отсутствует токен {token}. '
                'Бот не может продолжить работу.'
            )
            raise ValueError(f'Токен {token} недоступен.')
        else:
            return all(tokens)


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    try:
        logging.info('Начало отправки сообщения в Telegram')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logging.error('Ошибка отправки сообщения в Telegram.')
        raise TelegramError(
            f'Ошибка отправки сообщения в Telegram: {error}'
        )
    else:
        logging.debug('Сообщениe отправлено в Telegram.')


def get_api_answer(timestamp):
    """Запрос к API."""
    try:
        logging.info('Выполняется запрос к API.')
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        raise WrongGetApiAnswer(f'Ошибка запроса к API: {error}')
    if response.status_code != 200:
        raise WrongGetApiAnswer(
            'Неверный статус ответа API. '
            f'Код ответа {response.status_code}.'
        )
    else:
        logging.debug('Ответ API получен.')
        return response.json()


def check_response(response):
    """Проверка ответа API."""
    logging.info('Проводим проверки ответа API.')
    if not isinstance(response, dict):
        raise TypeError('Ответ не содержит словарь.')
    if 'homeworks' not in response:
        raise WrongCheckResponse('Отсутствует ключ homeworks.')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является list.')
    else:
        logging.debug('Ответ API содержит homeworks.')
        return homeworks


def parse_status(homework):
    """Извлечение информации о статусе работы."""
    logging.info('Извлекаем информацию о статусе работы.')
    if 'homework_name' not in homework:
        raise WrongParseStatus('Отсутствует ключ homework_name.')
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        raise WrongParseStatus('Отсутствует ключ status.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise WrongParseStatus(f'Неизвестный статус работы - {status}')
    else:
        verdict = HOMEWORK_VERDICTS[status]
        logging.debug('Информация о статусе работы получена.')
        return (f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Бот остановлен.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    logging.info('Бот начал работу.')
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Нет новых статусов.'
            send_message(bot, message)
            logging.debug('Бот успешно закончил работу.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(
                filename='main.log', mode='w', encoding='UTF-8'),
            logging.StreamHandler(stream=sys.stdout)
        ],
        format='%(asctime)s, %(levelname)s, %(message)s',
    )
    main()
