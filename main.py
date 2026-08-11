import requests
import time
import json
import os
from dotenv import load_dotenv
from tg_methods import TgMethods

load_dotenv()
# Подгрузка секретов из .env
token = os.getenv('TELEGRAM_SECRET')

# Ваш токен, полученный от @BotFather
TOKEN = token
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'

def main():
    """
    Главный цикл бота.
    Эквивалент bot.polling() из pytelegrambotapi
    """
    print('Бот запущен. Ожидание сообщений...')
    last_update_id = 0
    
    while True:
        try:
            # Получаем новые обновления
            updates = TgMethods.get_updates(offset=last_update_id + 1)
            
            for update in updates:
                # Сохраняем ID обновления, чтобы не получать его снова
                if update.get('update_id', 0) > last_update_id:
                    last_update_id = update['update_id']
                
                # Обрабатываем текстовые сообщения
                if 'message' in update:
                    message = update['message']
                    chat_id = message['chat']['id']
                    user_id = message['from']['id']
                    text = message.get('text', '')
                    TgMethods.handle_message(chat_id, user_id, message)
                                
                # Обрабатываем callback-запросы (если добавите инлайн-кнопки)
                elif 'callback_query' in update:
                    callback = update['callback_query']
                    chat_id = callback['message']['chat']['id']
                    data = callback['data']
                    callback_id = callback['id']
                    TgMethods.handle_callback_query(callback_id, chat_id, data)
        
        except Exception as e:
            print(f'Ошибка: {e}')
            time.sleep(5)

if __name__ == '__main__':
    main()

