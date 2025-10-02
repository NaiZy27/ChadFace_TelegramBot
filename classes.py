from telebot.async_telebot import types
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from pay import payments
import uuid
import os

load_dotenv()

channel = os.getenv('TG_CHANNEL')
support = os.getenv('SUPPORT')

def create_payment(value, id, menu_id, amount):
    Configuration.configure('1136840', 'live_7t-GxgQlqZPJp8m_EuTu0Gcr2bx7YW7s91w9yjD72K4')
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create({
        'amount': {
        'value': f'{value}',
        'currency': 'RUB'
        },
        "payment_method_data": {
        "type": "sbp"
        },
        'confirmation': {
        'type': 'redirect',
        'return_url': 'https://t.me/chadface_bot'
        },
        'description': 'Оплата токенов',
        'capture': True,
    }, idempotence_key)
    link = payment.confirmation.confirmation_url
    payments[link] = (id, amount, menu_id)
    return link


class Keyboard:
    def __init__(self):
        self.markup = types.InlineKeyboardMarkup()


class MembershipKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        btn1 = types.InlineKeyboardButton(text='Подписаться', url=channel)
        btn2 = types.InlineKeyboardButton(text='✅ Проверить подписку', callback_data='check_membership')
        self.markup.row(btn1)
        self.markup.row(btn2)


class MenuKeyboard(Keyboard):
    def __init__(self, balance):
        super().__init__()
        balance_btn = types.InlineKeyboardButton(text=f'💎 Токенов {balance}', callback_data='update_balance')
        btn1 = types.InlineKeyboardButton(text='📸 Оценка внешности', callback_data='check_rating')
        btn2 = types.InlineKeyboardButton(text='💸 Купить токен', callback_data='top_up_balance') 
        btn3 = types.InlineKeyboardButton(text='🛠️ Поддержка', callback_data='get_support')
        self.markup.row(balance_btn)
        self.markup.row(btn1)
        self.markup.row(btn2, btn3)


class MenuKeyboardNoLimit(Keyboard):
    def __init__(self):
        super().__init__()
        balance_btn = types.InlineKeyboardButton(text=f'💎 Токенов ♾️', callback_data='update_balance')
        btn1 = types.InlineKeyboardButton(text='📸 Оценка внешности', callback_data='check_rating')
        btn2 = types.InlineKeyboardButton(text='💸 Купить токен', callback_data='top_up_balance') 
        btn3 = types.InlineKeyboardButton(text='🛠️ Поддержка', callback_data='get_support')
        self.markup.row(balance_btn)
        self.markup.row(btn1)
        self.markup.row(btn2, btn3)


class SupportKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        btn1 = types.InlineKeyboardButton(text='Перейти ↗️', url=support)
        btn2 = types.InlineKeyboardButton(text='Назад', callback_data='main_menu')
        self.markup.row(btn1)
        self.markup.row(btn2)


class BackKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        btn1 = types.InlineKeyboardButton(text='Назад', callback_data='main_menu')
        self.markup.row(btn1)


class PaymentKeyboard(Keyboard):
    def __init__(self, id, menu_id):
        super().__init__()
        btn1 = types.InlineKeyboardButton(text='💎 3 (125.00 RUB)', url=create_payment(125.00, id, menu_id, 3), callback_data='check_payment')
        btn2 = types.InlineKeyboardButton(text='💎 5 (200.00 RUB)', url=create_payment(200.00, id, menu_id, 5), callback_data='check_payment') 
        btn3 = types.InlineKeyboardButton(text='💎 10 (350.00 RUB)', url=create_payment(350.00, id, menu_id, 10), callback_data='check_payment')
        btn4 = types.InlineKeyboardButton(text='💎 25 (500.00 RUB)', url=create_payment(500.00, id, menu_id, 25), callback_data='check_payment')
        btn5 = types.InlineKeyboardButton(text='💎 Безлимит (1000.00 RUB)', url=create_payment(1000.00, id, menu_id, 999999), callback_data='check_payment')
        btn6 = types.InlineKeyboardButton(text='Назад', callback_data='main_menu')
        self.markup.row(btn1, btn2)
        self.markup.row(btn3, btn4)
        self.markup.row(btn5)
        self.markup.row(btn6)

class DeleteKeyboard(Keyboard):
    def __init__(self):
        super().__init__()
        btn1 = types.InlineKeyboardButton(text='🗑 Удалить', callback_data='del_notification')
        self.markup.row(btn1)
