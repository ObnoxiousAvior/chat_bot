import re
from datetime import datetime
from weather_api import get_weather
from db import init_db

import spacy

class DialogState:
    START = "start"
    WAIT_CITY = "wait_city"
    WAIT_DATE = "wait_date"

class ChatBot:
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_sm")
        self.patterns = []
        self._register_patterns()
        
        self.user_states = {}
        self.user_data = {}

        self.log_intent = None
        self.log_city = None

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

    def _get_state(self, user_id):
        return self.user_states.get(user_id, DialogState.START)
    def _set_state(self, user_id, state):
        self.user_states[user_id] = state
    def _get_user_data(self, user_id):
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        return self.user_data[user_id]

    def _extract_city(self, text):
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("LOC", "GPE"):
                lemmas = [token.lemma_ for token in ent]
                return " ".join(lemmas).strip()
        return None
    def _is_weather_query(self, text):
        keywords = ["погода", "прогноз", "температура", "градус", "потепление", "похолодание"]
        return any(kw in text.lower() for kw in keywords)
    def _process_nlp(self, text):
        if self._is_weather_query(text):
            city = self._extract_city(text)
            if city:
                return get_weather(city), "weather", city
            else:
                return "Укажите город в вашем запросе.", "weather_unknown", None
        return None

    def greet(self, match): return "Здравствуйте! Чем могу помочь?"
    def farewell(self, match): return "До свидания!"
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
    def unknown(self, match): return "Извините, я не понимаю ваш запрос."

    def process(self, user_id: str, message: str) -> str:
        state = self._get_state(user_id)
        data = self._get_user_data(user_id)
        
        self.log_intent = None
        self.log_city = None

        if state == DialogState.START:
            if self._is_weather_query(message):
                city = self._extract_city(message)
                if city:
                    response = get_weather(city)
                    self.log_intent = "weather"
                    self.log_city = city
                    return response
                else:
                    self._set_state(user_id, DialogState.WAIT_CITY)
                    self.log_intent = "ask_city"
                    return "В каком городе вас интересует погода?"
            
            for pattern, handler in self.patterns:
                if match := pattern.search(message):
                    response = handler(match)
                    if handler == self.greet:
                        self.log_intent = "greet"
                    elif handler == self.farewell:
                        self.log_intent = "farewell"
                    elif handler == self.addition:
                        self.log_intent = "addition"
                    elif handler == self.time:
                        self.log_intent = "time"
                    else:
                        self.log_intent = "unknown"
                    return response
            
            self.log_intent = "unknown"
            return self.unknown()

        elif state == DialogState.WAIT_CITY:
            city = message.strip()
            if city:
                data['city'] = city
                self._set_state(user_id, DialogState.WAIT_DATE)
                self.log_intent = "ask_date"
                return "На какую дату?"
            else:
                return "Пожалуйста, укажите город."

        elif state == DialogState.WAIT_DATE:
            date = message.strip()
            city = data.get('city')
            if city and date:
                response = get_weather(city, date)
                del self.user_data[user_id]
                self._set_state(user_id, DialogState.START)
                self.log_intent = "weather_with_date"
                self.log_city = city
                return response
            else:
                self._set_state(user_id, DialogState.START)
                return "Произошла ошибка. Попробуйте сначала."

        return self.unknown()