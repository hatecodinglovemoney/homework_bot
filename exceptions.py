class WrongGetApiAnswer(Exception):
    """Неверный статус ответа API"""
    pass


class TelegramError(Exception):
    """Ошибка отправки сообщения в Telegram"""
    pass


class WrongCheckResponse(Exception):
    """Неверное содержание ответа API"""
    pass


class WrongParseStatus(Exception):
    """Неверное содержание ответа API"""
    pass
