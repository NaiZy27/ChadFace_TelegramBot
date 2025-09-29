from classes import MenuKeyboard, MembershipKeyboard, SupportKeyboard, BackKeyboard, PaymentKeyboard, MenuKeyboardNoLimit
from pay import payments
from telebot.async_telebot import AsyncTeleBot
import asyncio
import uvicorn
from google.genai import types
from google import genai
from dotenv import load_dotenv
import os
import db
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio

app = FastAPI()

load_dotenv()

token = os.getenv('TG_BOT_TOKEN')
bot = AsyncTeleBot(token)
key = os.getenv('API_KEY')
prompt = os.getenv('PROMPT')
menu = os.getenv('MENU')

users_states = {}

@app.post('/')
async def func(mode: Request):
    t = await mode.json()
    id = t['object']['id']
    await successful_payment(id)
    return JSONResponse(content={}, status_code=200)


async def on_startup():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())


async def successful_payment(payment_id):
    for key in payments:
        if payment_id in key:
            user_id = payments[key][0]
            menu_id = payments[key][2]
            await db.top_up_balance(payments[key][0], payments[key][1])
            message = await bot.send_message(payments[key][0], text=f'Оплата прошла успешно! 🎉\n\nСумма пополнения - {payments[key][1]} 💎')
            afterward = list(filter(lambda a: a == user_id, payments))
            for payment in afterward:
                payments.pop(payment)
            await asyncio.sleep(10)
            await create_menu(user_id, mode=None, payment=True, message=message, menu_id=menu_id)
            break


@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    if await db.find_user(user_id) == None:
        await db.create_user(user_id)
    user_member = await bot.get_chat_member('@chadface_channel', user_id)
    if user_member.status in ['member', 'administrator', 'creator']:
        await create_menu(user_id)
    else:
        keyboard = MembershipKeyboard()
        await bot.send_message(user_id, text='❗ ДЛЯ РАБОТЫ С БОТОМ ПОДПИШИТЕСЬ НА КАНАЛ', reply_markup=keyboard.markup)


@bot.message_handler(func=lambda message: True)
async def delete_user_message(message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


async def create_menu(user_id, mode=False, payment=False, message=None, menu_id=None):
    user = await db.find_user(user_id)
    if user.balance > 99999:
        menu_keyboard = MenuKeyboardNoLimit()
    else:
        menu_keyboard = MenuKeyboard(user.balance)    

    if mode == True:
        await bot.edit_message_caption(chat_id=user_id, message_id=message.message_id,
                                caption='🍷 Личный кабинет', reply_markup=menu_keyboard.markup)
    elif mode == False:
        await bot.send_photo(chat_id=user_id, photo=menu, caption='🍷 Личный кабинет', reply_markup=menu_keyboard.markup)
    
    if payment:
        await bot.delete_message(user_id, message.message_id)
        await bot.edit_message_caption(chat_id=user_id, message_id=menu_id,
                                caption='🍷 Личный кабинет', reply_markup=menu_keyboard.markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('main_menu'))
async def main_menu(call):
    user_id = call.from_user.id
    await create_menu(user_id=user_id, mode=True, payment=False, message=call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('check_membership'))
async def check_membership(call):
    user_id = call.from_user.id
    if await db.find_user(user_id) == None:
        await db.create_user(user_id)
    user_member = await bot.get_chat_member('@chadface_channel', user_id)
    if user_member.status in ['member', 'administrator', 'creator']:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await create_menu(user_id)
    else:
        await start(call)
         

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_rating'))
async def get_photo1(call):
    user_id = call.from_user.id
    user = await db.find_user(user_id)
    back_keyboard = BackKeyboard()
    if user.balance > 0:
        await bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id,
                                caption='Пришлите фото ⬇️',
                                reply_markup=back_keyboard.markup)
        users_states[user_id] = 'WAITING_FOR_PHOTO'
    else:
        await bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id,
                                caption='❌ У вас нет токенов, если хотите получить оценку внешности - пополните баланс',
                                reply_markup=back_keyboard.markup)


@bot.message_handler(func=lambda message: users_states[message.from_user.id] == 'WAITING_FOR_PHOTO', content_types=['photo'])
async def get_photo2(message):
    photo = message.photo[-1].file_id
    await rate_photo(message, photo)
    

async def rate_photo(message, photo):
    user_id = message.from_user.id
    client = genai.Client(api_key=key)
    file_info = await bot.get_file(photo)
    image_bytes = await bot.download_file(file_info.file_path)
    analysis_message = await bot.send_message(message.from_user.id, text='🔍 Анализ фотографии . . .')
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type='image/jpeg',
            ),
            prompt
        ]
    )
    answer = response.text
    await bot.delete_message(chat_id=message.from_user.id, message_id=analysis_message.message_id)
    await bot.send_photo(message.from_user.id, photo=photo, caption='🍷 Результат анализа фотографии:')
    await bot.send_message(message.from_user.id, text=answer)
    await db.charge_off_balance(user_id)
    del users_states[user_id]
    await asyncio.sleep(10)
    await create_menu(user_id)
    

@bot.callback_query_handler(func=lambda call: call.data.startswith('top_up_balance'))
async def top_up_balance(call):
    user_id = call.from_user.id
    menu_id = call.message.message_id
    payment_keyboard = PaymentKeyboard(user_id, menu_id)
    await bot.edit_message_caption(chat_id=user_id, message_id=menu_id,
                             caption='🍷 Выберите количество токенов',
                             reply_markup=payment_keyboard.markup)
       

@bot.callback_query_handler(func=lambda call: call.data.startswith('get_support'))
async def get_support(call):
    user_id = call.from_user.id
    support_keyboard = SupportKeyboard()
    await bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id,
                             caption='🍷 Поддержка работает с 08 до 23 по МСК. Ваше обращение обязательно будет рассмотрено',
                             reply_markup=support_keyboard.markup)


async def main():
    await db.create_db()
    await on_startup()
    await bot.polling(none_stop=True, interval=0)


if __name__ == '__main__':
    asyncio.run(main())
