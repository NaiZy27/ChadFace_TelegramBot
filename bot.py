from classes import MenuKeyboard, MembershipKeyboard, SupportKeyboard, BackKeyboard, MenuKeyboardNoLimit, DeleteKeyboard, get_payment_keyboard
from ref import ref_codes
from pay import payments
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
import uvicorn
from google.genai import types
from google import genai
from dotenv import load_dotenv
import os
import db
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio

load_dotenv()

key = os.getenv('API_KEY')
client = genai.Client(api_key=key)
prompt = os.getenv('PROMPT')
gemini_semaphore = asyncio.Semaphore(20)

app = FastAPI()
token = os.getenv('TG_BOT_TOKEN')
bot = Bot(token=token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
menu = os.getenv('MENU')


class UserState(StatesGroup):
    waiting_for_photo = State()


@app.post('/')
async def func(mode: Request):
    request_data = await mode.json()
    id = request_data['object']['id']
    await successful_payment(id)
    return JSONResponse(content={}, status_code=200)


async def on_startup():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())


async def successful_payment(payment_id):
    for key in payments:
        if payment_id in key:
            user_id, amount, value = payments[key]
            del payments[key]
            await db.top_up_balance(user_id, amount, value)
            close_keyboard = DeleteKeyboard()
            if amount != 0:
                await bot.send_message(chat_id=user_id, text=f'🎉 Оплата прошла успешно!\n\n\n💎 Пополнено токенов - {amount}', reply_markup=close_keyboard.markup)
            else:
                await bot.send_message(chat_id=user_id, text='🎉 Оплата прошла успешно!\n\n\n💎 У вас безлимит', reply_markup=close_keyboard.markup)
            break


@router.callback_query(F.data.startswith('del_notification'))
async def del_notification(call: CallbackQuery):
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    await bot.answer_callback_query(callback_query_id=call.id, text='💥 Уведомление удалено')


@router.message(Command('start'))
async def start(message: Message, state: FSMContext):
    ref_code = message.text.split()[1] if len(message.text.split()) > 1 else None
    user_id = message.from_user.id
    if await db.find_user(user_id) is None:
        await db.create_user(user_id)
        if ref_code in ref_codes:
            await db.top_up_balance(user_id, 1, 0)
            await db.adjust_referal(user_id, ref_code)
    user_member = await bot.get_chat_member(chat_id='@chadface_channel', user_id=user_id)
    if user_member.status in ['member', 'administrator', 'creator']:
        await create_menu(user_id, state=state)
    else:
        keyboard = MembershipKeyboard()
        await bot.send_message(chat_id=user_id, text='❗ ДЛЯ РАБОТЫ С БОТОМ ПОДПИШИТЕСЬ НА КАНАЛ', reply_markup=keyboard.markup)
    await bot.delete_message(chat_id=user_id, message_id=message.message_id)


async def create_menu(user_id: int, state: FSMContext, mode=False, message=None, menu_id=None):
    user = await db.find_user(user_id)
    await state.clear()
    if user.unlimit:
        menu_keyboard = MenuKeyboardNoLimit()
    else:
        menu_keyboard = MenuKeyboard(user.balance)

    if mode:
        target_id = menu_id if menu_id is not None else message.message_id
        await bot.edit_message_caption(chat_id=user_id, message_id=target_id,
                            caption='🍷 Личный кабинет', reply_markup=menu_keyboard.markup)
    else:
        await bot.send_photo(chat_id=user_id, photo=menu, caption='🍷 Личный кабинет', reply_markup=menu_keyboard.markup)


@router.callback_query(F.data.startswith('main_menu'))
async def main_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    await create_menu(user_id=user_id, state=state, mode=True, message=call.message, menu_id=None)


@router.callback_query(F.data.startswith('check_membership'))
async def check_membership(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if await db.find_user(user_id) is None:
        await db.create_user(user_id)
    user_member = await bot.get_chat_member('@chadface_channel', user_id)
    if user_member.status in ['member', 'administrator', 'creator']:
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await create_menu(user_id=user_id, state=state)
    else:
        await bot.answer_callback_query(callback_query_id=call.id, text='❗ Вы не подписаны!')
         

@router.callback_query(F.data.startswith('check_rating'))
async def get_photo1(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    user = await db.find_user(user_id)
    back_keyboard = BackKeyboard()
    if user.balance > 0 or user.unlimit:
        await bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id,
                                caption='Пришлите фото ⬇️',
                                reply_markup=back_keyboard.markup)
        await state.update_data(message_id=call.message.message_id)
        await state.set_state(UserState.waiting_for_photo)

    else:
        await bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id,
                                caption='❌ У вас нет токенов, если хотите получить оценку внешности - пополните баланс',
                                reply_markup=back_keyboard.markup)


@router.message(UserState.waiting_for_photo, F.photo)
async def get_photo2(message: Message, state: FSMContext):
    photo = message.photo[-1].file_id
    data = await state.get_data()
    message_id = data.get('message_id')
    await state.update_data(photo_id=photo, photo_message_id=message.message_id)
    await rate_photo(message, photo, message_id, state)
    

async def rate_photo(message: Message, photo: str, menu_id: int, state: FSMContext):
    user_id = message.from_user.id
    file_info = await bot.get_file(photo)
    image_io = await bot.download_file(file_info.file_path)
    image_bytes = image_io.getvalue()
    await bot.send_photo(chat_id=user_id, photo=photo)
    await bot.delete_message(chat_id=user_id, message_id=menu_id)
    analysis_message = await bot.send_message(chat_id=user_id, text='🔍 Анализ фотографии . . .')
    photo_data = await state.get_data()
    photo_message_id = photo_data.get('photo_message_id')
    await bot.delete_message(chat_id=user_id, message_id=photo_message_id)
    async with gemini_semaphore:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                    prompt
                ]
            )
        )
        answer = f'🍷 Результат анализа фотографии:\n\n{response.text}'
        await bot.delete_message(chat_id=user_id, message_id=analysis_message.message_id)
        await bot.send_message(chat_id=user_id, text=answer)
        await state.clear()
        await db.charge_off_balance(user_id)
        asyncio.create_task(delayed_create_menu(user_id, delay=7))


async def delayed_create_menu(user_id: int, delay: int):
    await asyncio.sleep(delay)
    state = FSMContext(storage=storage, key=f"user:{user_id}")
    await create_menu(user_id, state=state)
    

@router.callback_query(F.data.startswith('top_up_balance'))
async def top_up_balance(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    menu_id = call.message.message_id
    payment_keyboard = await get_payment_keyboard(user_id)
    await bot.edit_message_caption(chat_id=user_id, message_id=menu_id,
                             caption='🍷 Выберите количество токенов\n\n❗ 1 токен  —  1 оценка внешности',
                             reply_markup=payment_keyboard)
       

@router.callback_query(F.data.startswith('get_support'))
async def get_support(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    support_keyboard = SupportKeyboard()
    await bot.edit_message_caption(chat_id=user_id, message_id=call.message.message_id,
                             caption='🍷 Поддержка работает с 08 до 23 по МСК',
                             reply_markup=support_keyboard.markup)
    

@router.message(UserState.waiting_for_photo)
async def delete_non_photo_messages(message: Message):
    if message.photo:
        return
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@router.message(~StateFilter(UserState.waiting_for_photo))
async def delete_user_message(message: Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


async def main():
    await db.create_db()
    await on_startup()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
