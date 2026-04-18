from bot_core import ChatBot
from db import save_log

def main():
    bot = ChatBot()

    print("Приложение чат-бота, выполняющего базовые команды.\n===================\n")
    print("Бот: Привет! Я бот. Я умею:\n- Показывать погоду\n- Складывать числа\n- Показывать время.\n")

    while True:
        if not (user_input := input("Вы: ").strip()): 
            continue

        response = bot.process(user_input)
        print("Бот:", response)

        save_log(user_input, response)

        if response == "До свидания!": 
            break

if __name__ == "__main__":
    main()