from bot_core import ChatBot
from db import log

def main():
    bot = ChatBot()
    user_id = "default"

    print("Приложение чат-бота, выполняющего базовые команды.\n===================\n")
    print("Бот: Привет! Я бот. Я умею:\n- Показывать погоду\n- Складывать числа\n- Показывать время.\n")

    while True:
        if not (user_input := input("Вы: ").strip()): 
            continue

        response = bot.process(user_id, user_input)
        print("Бот:", response)

        log(user_input, response, bot.log_intent, bot.log_city)

        if response == "До свидания!": 
            break

if __name__ == "__main__":
    main()