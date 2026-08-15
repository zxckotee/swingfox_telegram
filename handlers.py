import copy
from swinger import *
from tg_methods import TgMethods

def registration(chat_id, user_id, message):
    user_state = Swinger.getUserState(user_id)
    
    if (user_state is None):
        TgMethods.send_message(chat_id, "Приветствую! Хочешь завести свингерские знакомства? Тогда пора регистрироваться!")
        
        data = {
            "registration": {}
        }
        Swinger.setUserState(user_id, "registration_type", data)
        buttons = [
            ["Мужчина", "Женщина"],
            ["Семейная пара", "Несемейная пара"]
        ]
        reply_markup = TgMethods.create_reply_keyboard(buttons)
        TgMethods.send_message(chat_id, "Укажи свой пол или тип пары:", reply_markup)
    else:
        
        if (user_state.status == "registration_type"):
            data = copy.deepcopy(user_state.data)
            options = ["Мужчина", "Женщина", "Семейная пара", "Несемейная пара"]
            
            if (message['text'] in options):
                data['registration']['type'] = message['text']
                match message['text']:
                    case "Мужчина":
                        persons={"man": {}}
                        mess = "Как тебя зовут?"
                    case "Женщина":
                        persons={"woman": {}}
                        mess = "Как тебя зовут?"
                    case "Семейная пара" | "Несемейная пара":
                        persons={"man": {}, "woman": {}}
                        mess = "Как зовут Мужчину?"
                TgMethods.send_message(chat_id, mess, reply_markup={'remove_keyboard': True})

                data['registration']['persons'] = persons
                print(f"поставили нормальный объект data: {data}")
                Swinger.setUserState(user_id, 'registration_name', data)
                print("проверка get метода", Swinger.getUserState(user_id).data)
                
            else:
                TgMethods.send_message(chat_id, "Нет такого варианта ответа..")

        elif (user_state.status == "registration_name"):
            def second_person():
                TgMethods.send_message(chat_id, "Как зовут Женщину?")

            data = copy.deepcopy(user_state.data)
            print(data)
            persons = data['registration']['persons']
            type = data['registration']['type']
            if (type in ["Мужчина", "Женщина"]):
                if type=='Мужчина':
                    persons["man"]["name"] = message['text']
                elif type=='Женщина':
                    persons["woman"]["name"] = message['text']
                data['registration']["persons"] = persons
                TgMethods.send_message(chat_id, "Сколько тебе лет?")
                Swinger.setUserState(user_id, 'registration_age', data)

            elif (user_state.data['registration']['type'] in ["Семейная пара", "Несемейная пара"]):
                if (persons['man'] == {} and persons['woman'] == {}):
                    persons['man']["name"] = message['text']
                    data['registration']["persons"] = persons
                    Swinger.setUserState(user_id, 'registration_name', data)
                    # один есть, второго нету, отправляем на второй круг
                    second_person()
                elif persons['woman'] == {} and persons['man'] != {}:
                    persons['woman']["name"] = message['text']
                    data['registration']["persons"] = persons
                    # можно завершать этап, оба есть
                    Swinger.setUserState(user_id, 'registration_age', data)
                    TgMethods.send_message(chat_id, "Сколько лет Мужчине?")

        elif (user_state.status == "registration_age"):
            def second_person():
                TgMethods.send_message(chat_id, "Сколько лет Женщине?")

            data = copy.deepcopy(user_state.data)
            persons = data['registration']['persons']
            type = data['registration']['type']
            if (type in ["Мужчина", "Женщина"]):
                if type=='Мужчина':
                    persons["man"]["age"] = message['text']
                elif type=='Женщина':
                    persons["woman"]["age"] = message['text']
                data['registration']["persons"] = persons
                Swinger.setUserState(user_id, 'registration_want_type', data)
                buttons = [
                    ["Мужчину", "Женщину"],
                    ["Семейную пару", "Несемейную пару"],
                    ["Любую пару", "Без разницы"]
                ]
                reply_markup = TgMethods.create_reply_keyboard(buttons)
                TgMethods.send_message(chat_id, "Кого хочешь найти?", reply_markup)      

            elif (user_state.data['registration']['type'] in ["Семейная пара", "Несемейная пара"]):
                if (persons['man'] == {} and persons['woman'] == {}):
                    persons['man']["age"] = message['text']
                    data['registration']["persons"] = persons
                    Swinger.setUserState(user_id, 'registration_age', data)
                    # один есть, второго нету, отправляем на второй круг
                    second_person()
                elif persons['woman'] == {} and persons['man'] != {}:
                    persons['woman']["age"] = message['text']
                    data['registration']["persons"] = persons
                    # можно завершать этап, оба есть
                    Swinger.setUserState(user_id, 'registration_want_type', data)
                    buttons = [
                        ["Мужчину", "Женщину"],
                        ["Семейную пару", "Несемейную пару"],
                        ["Любую пару", "Без разницы"]
                    ]
                    reply_markup = TgMethods.create_reply_keyboard(buttons)
                    TgMethods.send_message(chat_id, "Кого хочешь найти?", reply_markup)      

        elif (user_state.status == "registration_want_type"):
            options = ["Мужчину", "Женщину", "Семейную пару", "Несемейную пару", "Любую пару", "Без разницы"]
            data = copy.deepcopy(user_state.data)

            if (message['text'] in options):
                # ПРОПИСАТЬ СОЗДАНИЕ АККАУНТА -- готово
                persons = data['registration']['persons']
                type = data['registration']['type']
                Swinger.createAccount(user_id, persons, type , message['text'], False) # на этом этапе в message['text'] у нас содержиться как раз want_type
                
                mess = "Ты успешно зарегистрирован! Начинай знакомиться!"
                TgMethods.send_message(chat_id, mess, reply_markup={'remove_keyboard': True})
                

                Swinger.setUserState(user_id, "watch_profiles", data)
                
            else:
                TgMethods.send_message(chat_id, "Нет такого варианта ответа..")