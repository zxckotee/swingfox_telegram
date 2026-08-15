import requests
import time
import json
import os
from dotenv import load_dotenv
from swinger import *

load_dotenv()
# Подгрузка секретов из .env
token = os.getenv('TELEGRAM_SECRET')

# Ваш токен, полученный от @BotFather
TOKEN = token
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'

system_commands = ["/start"]


class TgMethods:

    @staticmethod
    def handle_message(chat_id, user_id, message):
        
        if (Swinger.checkAccount(user_id) == False):
            from handlers import registration
            registration(chat_id, user_id, message) # перенаправляем на регистрацию

            

    @staticmethod
    def create_reply_keyboard(buttons, resize_keyboard=True):
        """
        Создает клавиатуру с кнопками.
        Эквивалент types.ReplyKeyboardMarkup() из pytelegrambotapi
        """
        keyboard = {
            'keyboard': buttons,
            'resize_keyboard': resize_keyboard
        }
        return keyboard
    
    @staticmethod
    def create_inline_keyboard(buttons):
        """
        Создает инлайн-клавиатуру.
        Эквивалент types.InlineKeyboardMarkup() из pytelegrambotapi
        """
        keyboard = {
            'inline_keyboard': [[{
                'text': btn['text'],
                'url': btn.get('url'),
                'callback_data': btn.get('callback_data')
            } for btn in row] for row in buttons]
        }
        return keyboard



    @staticmethod
    def send_message(chat_id, text, reply_markup=None, parse_mode=None, entities=None):
        """
        Отправляет текстовое сообщение.
        Эквивалент bot.send_message() из pytelegrambotapi
        """
        url = f'{BASE_URL}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'entities': entities
        }
        
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        
        response = requests.post(url, data=payload)
        return response.json()

    @staticmethod
    def send_one_object(chat_id, media_group, files):
        media = media_group[0]
        filename = media['media'].replace('attach://', '')
        params = {
            'chat_id': chat_id,
        }
        if (media['type'] == 'photo'):
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            params['photo'] = f"attach://{filename}"
        elif (media['type'] == 'voice'):
            url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
            params['voice'] = f"attach://{filename}"
        elif (media['type'] == 'video'):
            params['video'] = f"attach://{filename}"
            url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"

        response = requests.post(url, data=params, files=files)
        print (params, response)
        return response
        

    @staticmethod           # Отправляет медиагруппу
    def send_media_group(chat_id, media_group, files):
        params = {
            'chat_id': chat_id,
            'media': json.dumps(media_group)
        }
        print (files)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMediaGroup"
        response = requests.post(url, data=params, files=files)

        return response # ответ - объект Message
         
    @staticmethod
    def get_updates(offset=None, timeout=30):
        """
        Получает новые обновления от Telegram.
        Эквивалент getUpdates из официального API
        """
        url = f'{BASE_URL}/getUpdates'
        params = {
            'timeout': timeout,
            'allowed_updates': ['message', 'callback_query']
        }
        
        if offset:
            params['offset'] = offset
        
        response = requests.get(url, params=params)
        return response.json().get('result', [])
        

    @staticmethod
    def handle_callback_query(callback_query_id, chat_id, data):
        """
        Обрабатывает callback-запросы от инлайн-кнопок.
        """
        # Пример обработки callback (если добавите инлайн-кнопки)
        answer_callback = f'{BASE_URL}/answerCallbackQuery'
        requests.post(answer_callback, data={
            'callback_query_id': callback_query_id,
            'text': f'Вы нажали кнопку: {data}',
            'show_alert': False
        })
        
        TgMethods.send_message(chat_id, f'Вы выбрали: {data}')

