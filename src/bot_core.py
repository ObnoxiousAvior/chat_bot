import re
import joblib
import spacy

from datetime import datetime
from weather_api import get_weather
from db import init_db

class DialogState:
    START = "start"
    WAIT_CITY = "wait_city"
    WAIT_DATE = "wait_date"

class ChatBot:
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_sm")

        self.model = joblib.load("model.pkl")
        self.classes = self.model.classes_

        self.user_states = {}
        self.user_data = {}
        self.log_intent = None
        self.log_city = None

        init_db()

    def _preprocess(self, text):
        doc = self.nlp(text)
        tokens = []
        for token in doc:
            if not token.is_stop and not token.is_punct:
                tokens.append(token.lemma_)
        return " ".join(tokens)
    def _predict_intent(self, text):
        vec = self.nlp(text).vector.reshape(1, -1)
        proba = self.model.predict_proba(vec)[0]
        confidence = max(proba)
        intent = self.model.predict(vec)[0]
        return intent, confidence
    
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
    def _extract_numbers(self, text):
        return [float(x) for x in re.findall(r"\d+\.?\d*", text)]

    def greet(self):
        return "Здравствуйте! Чем могу помочь?"
    def farewell(self):
        return "До свидания!"
    def addition(self, text):
        nums = self._extract_numbers(text)
        if len(nums) >= 2:
            return f"Результат: {nums[0] + nums[1]}"
        return "Не удалось распознать числа. Напишите, например: сумма 5 10"
    def time(self):
        return datetime.now().strftime("Сейчас время %H:%M:%S, %d.%m.%Y")
    def unknown(self):
        return "Извините, я не понимаю ваш запрос."

    def process(self, user_id: str, message: str) -> str:
        state = self._get_state(user_id)
        data = self._get_user_data(user_id)
        
        self.log_intent = None
        self.log_city = None

        if state == DialogState.START:

            intent, conf = self._predict_intent(message)
            if conf < 0.5:
                self.log_intent = "low_confidence"
                return "Не уверен в ответе."
            
            self.log_intent = intent

            if intent == "greeting":
                return self.greet()
            elif intent == "goodbye":
                return self.farewell()
            elif intent == "addition":
                return self.addition(message)
            elif intent == "time":
                return self.time()
            elif intent == "weather":
                city = self._extract_city(message)
                if city:
                    data['city'] = city
                    self._set_state(user_id, DialogState.WAIT_DATE)
                    self.log_intent = "weather_ask_date"
                    return "На какую дату?"
                else:
                    self._set_state(user_id, DialogState.WAIT_CITY)
                    self.log_intent = "weather_ask_city"
                    return "В каком городе?"
            else:
                return self.unknown
            
        elif state == DialogState.WAIT_CITY:
            city = message.strip()
            if city:
                data['city'] = city
                self._set_state(user_id, DialogState.WAIT_DATE)
                self.log_intent = "weather_ask_date"
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