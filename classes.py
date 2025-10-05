from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from pay import payments
import asyncio
import uuid
import os

load_dotenv()

yookassa_token = os.getenv('YOOKASSA_TOKEN')
yookassa_id = os.getenv('YOOKASSA_ID')
channel = os.getenv('TG_CHANNEL')
support = os.getenv('SUPPORT')

Configuration.configure(yookassa_id, yookassa_token)


def _sync_create_payment(value, idempotence_key):
    return Payment.create({
        'amount': {'value': f'{value}', 'currency': 'RUB'},
        "payment_method_data": {"type": "sbp"},
        'confirmation': {
            'type': 'redirect',
            'return_url': 'https://t.me/chadface_bot'
        },
        'description': 'Оплата токенов',
        'capture': True,
    }, idempotence_key)


async def create_payment(value, user_id, amount):
    idempotence_key = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    payment = await loop.run_in_executor(None, _sync_create_payment, value, idempotence_key)
    link = payment.confirmation.confirmation_url
    payments[link] = (user_id, amount, int(value))
    return link


async def get_payment_keyboard(user_id):
    urls = await asyncio.gather(
        create_payment(125.00, user_id, 3),
        create_payment(200.00, user_id, 5),
        create_payment(350.00, user_id, 10),
        create_payment(500.00, user_id, 25),
        create_payment(1000.00, user_id, 0),
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='💎 3 (125₽)', url=urls[0]),
            InlineKeyboardButton(text='💎 5 (200₽)', url=urls[1])
        ],
        [
            InlineKeyboardButton(text='💎 10 (350₽)', url=urls[2]),
            InlineKeyboardButton(text='💎 25 (500₽)', url=urls[3])
        ],
        [
            InlineKeyboardButton(text='💎 Безлимит (1000₽)', url=urls[4])
        ],
        [
            InlineKeyboardButton(text='Назад', callback_data='main_menu')
        ]
    ])
    return markup


class Keyboard:
    def __init__(self):
        self.markup = InlineKeyboardMarkup(inline_keyboard=[])


class MembershipKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text='Подписаться', url=channel)],
            [InlineKeyboardButton(text='✅ Проверить подписку', callback_data='check_membership')]
        ]


class MenuKeyboard(Keyboard):
    def __init__(self, balance):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text=f'💎 Токенов {balance}', callback_data='update_balance')],
            [InlineKeyboardButton(text='📸 Оценка внешности', callback_data='check_rating')],
            [
                InlineKeyboardButton(text='💸 Купить токен', callback_data='top_up_balance'),
                InlineKeyboardButton(text='🛠️ Поддержка', callback_data='get_support')
            ]
        ]


class MenuKeyboardNoLimit(Keyboard):
    def __init__(self):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text='💎 Безлимит', callback_data='update_balance')],
            [InlineKeyboardButton(text='📸 Оценка внешности', callback_data='check_rating')],
            [InlineKeyboardButton(text='🛠️ Поддержка', callback_data='get_support')]
        ]


class SupportKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text='Подать обращение ↗️', url=support)],
            [InlineKeyboardButton(text='Назад', callback_data='main_menu')]
        ]


class BackKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text='Назад', callback_data='main_menu')]
        ]


class DeleteKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text='🗑 Удалить', callback_data='del_notification')]
        ]


class UpdateKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        self.markup.inline_keyboard = [
            [InlineKeyboardButton(text='🔄 Обновить', callback_data='update')]
        ]
