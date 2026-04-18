import re
from datetime import datetime
from weather_api import get_weather
from db import init_db

class ChatBot:
    def __init__(self):
        self.patterns = []
        self._register_patterns()
        init_db()

    def _register_patterns(self):
        self.patterns.append((re.compile(r"^(привет|здравствуйте)", re.IGNORECASE), self.greet))
        self.patterns.append((re.compile(r"^(пока|до свидания)", re.IGNORECASE), self.farewell))
        self.patterns.append((re.compile(r"^погода\s+(.+)", re.IGNORECASE), self.weather))
        self.patterns.append((re.compile(r"^сумма\s+(\d+\.?\d*)\s+(\d+\.?\d*)", re.IGNORECASE), self.addition))
        self.patterns.append((re.compile(
            r"(сколько времени|который час|текущее время|дата и время|какой сегодня день|какая дата|какое сегодня число)",
            re.IGNORECASE), self.time))
        self.default_handler = self.unknown

    def greet(self, match):
        return "Здравствуйте! Чем могу помочь?"

    def farewell(self, match):
        return "До свидания!"

    def weather(self, match):
        city = match.group(1).strip()
        if not city:
            return "Укажите город."
        return get_weather(city)

    def addition(self, match):
        try:
            a = float(match.group(1))
            b = float(match.group(2))
            return f"Результат: {a + b}"
        except ValueError:
            return "Ошибка: введите два числа."

    def time(self, match):
        now = datetime.now()
        return now.strftime("Сейчас время %H:%M:%S, %d.%m.%Y")

    def unknown(self, match):
        return "Извините, я не понимаю ваш запрос."

    def process(self, message: str) -> str:
        for pattern, handler in self.patterns:
            match = pattern.search(message)
            if match:
                return handler(match)
        return self.default_handler(None)