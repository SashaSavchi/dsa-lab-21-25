import asyncio
import asyncpg
import re
import logging
import os
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from dotenv import load_dotenv

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_COMMAND = os.getenv("ADMIN_COMMAND")

# Параметры подключения к PostgreSQL
DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
}

async def create_db_pool():
    return await asyncpg.create_pool(**DB_CONFIG)

async def init_db():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            chat_id VARCHAR UNIQUE
        )
        ''')
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS currencies (
            id SERIAL PRIMARY KEY,
            currency_name VARCHAR UNIQUE,
            rate NUMERIC
        )
        ''')
    finally:
        await conn.close()

# URL микросервисов
CURRENCY_MANAGER_URL = "http://localhost:5001"
DATA_MANAGER_URL = "http://localhost:5002"

# Инициализация бота
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния
class CurrencyStates(StatesGroup):
    waiting_currency_name = State()
    waiting_currency_rate = State()
    waiting_convert_currency = State()
    waiting_convert_amount = State()
    waiting_new_rate = State()

# Валидация кода валюты
def validate_currency(currency: str) -> bool:
    return bool(re.fullmatch(r'^[A-Za-z]{3}$', currency))

# Главное меню
async def get_inline_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💱 Получить курсы валют", callback_data="get_currencies")
    builder.button(text="💸 Конвертировать валюту", callback_data="convert")
    if is_admin:
        builder.button(text="🛠 Управление валютами", callback_data="manage_currency")
    builder.adjust(1)
    return builder.as_markup()

# Админ-меню
async def get_currency_management_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить валюту", callback_data="add_currency")
    builder.button(text="➖ Удалить валюту", callback_data="delete_currency")
    builder.button(text="✏️ Изменить курс", callback_data="change_rate")
    builder.button(text="🚪 Выйти из админки", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()

# Обработчик /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    pool = dp["pool"]
    async with pool.acquire() as conn:
        admin = await conn.fetchrow("SELECT * FROM admins WHERE chat_id = $1", str(message.chat.id))
    is_admin = admin is not None
    menu = await get_inline_menu_keyboard(is_admin)

    if is_admin:
        response = (
            "💱 Бот для конвертации валют (администратор)\n\n"
            "Доступные команды:\n"
            "• Управление валютами\n"
            "• Получить курсы валют\n"
            "• Конвертировать валюту"
        )
    else:
        response = (
            "💱 Бот для конвертации валют\n\n"
            "Доступные команды:\n"
            "• Получить курсы валют\n"
            "• Конвертировать валюту"
        )

    await message.answer(response, reply_markup=menu)

# Получение курсов валют
@dp.callback_query(F.data == "get_currencies")
async def cb_get_currencies(callback: CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DATA_MANAGER_URL}/currencies")
        if response.status_code != 200:
            await callback.message.answer("Ошибка при получении курсов валют")
            return
        
        currencies = response.json()
        is_admin = callback.message.text == ADMIN_COMMAND
        menu = await get_inline_menu_keyboard(is_admin)

        if currencies:
            response_text = "Текущие курсы валют к рублю:\n" + "\n".join(
                f"- {currency['currency_name']}: {currency['rate']} RUB"
                for currency in currencies
            )
        else:
            response_text = "ℹ️ В базе данных нет сохраненных валют"

        await callback.message.edit_text(response_text, reply_markup=menu)
        await callback.answer()

# Конвертация валюты
@dp.callback_query(F.data == "convert")
async def cb_convert(callback: CallbackQuery, state: FSMContext):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DATA_MANAGER_URL}/currencies")
        if response.status_code != 200 or not response.json():
            await callback.message.answer("ℹ️ В базе нет валют для конвертации")
            await callback.answer()
            return

    await callback.message.answer("💸 Введите название валюты для конвертации (например: USD):")
    await state.set_state(CurrencyStates.waiting_convert_currency)
    await callback.answer()

@dp.message(CurrencyStates.waiting_convert_currency)
async def process_convert_currency(message: types.Message, state: FSMContext):
    currency = message.text.strip().upper()
    
    if not validate_currency(currency):
        await message.answer("❌ Неверный формат валюты! Введите 3 английские буквы (например: USD):")
        return

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DATA_MANAGER_URL}/convert", params={"currency_name": currency, "amount": 1})
        if response.status_code == 404:
            await message.answer(f"❌ Валюта {currency} не найдена! Попробуйте снова:")
            return
        
        rate = response.json()["converted_amount"]

    await state.update_data(currency=currency, rate=rate)
    await message.answer(f"Введите сумму в {currency} для конвертации в RUB:")
    await state.set_state(CurrencyStates.waiting_convert_amount)

@dp.message(CurrencyStates.waiting_convert_amount)
async def process_convert_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError

        data = await state.get_data()
        currency = data['currency']
        rate = data['rate']
        result = amount * rate
        await state.clear()

        is_admin = message.text == ADMIN_COMMAND
        menu = await get_inline_menu_keyboard(is_admin)

        await message.answer(
            f"Результат конвертации:\n"
            f"{amount} {currency} = {result:.2f} RUB\n"
            f"Курс: 1 {currency} = {rate} RUB",
            reply_markup=menu
        )
    except ValueError:
        await message.answer("❌ Ошибка! Введите положительное число:")

# Управление валютами (только для админов)
@dp.callback_query(F.data == "manage_currency")
async def cb_manage_currency(callback: CallbackQuery):
    if callback.message.text != ADMIN_COMMAND:
        await callback.answer("❌ Эта функция доступна только администраторам", show_alert=True)
        return
    
    menu = await get_currency_management_keyboard()
    await callback.message.edit_text("🛠 Управление валютами:", reply_markup=menu)
    await callback.answer()

# Добавление валюты
@dp.callback_query(F.data == "add_currency")
async def cb_add_currency(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код новой валюты (например: USD):")
    await state.set_state(CurrencyStates.waiting_currency_name)
    await callback.answer()

@dp.message(CurrencyStates.waiting_currency_name)
async def process_currency_name(message: types.Message, state: FSMContext):
    currency = message.text.strip().upper()
    if not validate_currency(currency):
        await message.answer("❌ Неверный формат валюты. Введите 3 английские буквы:")
        return

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DATA_MANAGER_URL}/currencies")
        currencies = [c["currency_name"] for c in response.json()]
        if currency in currencies:
            await message.answer(f"❌ Валюта {currency} уже существует. Введите другой код:")
            return

    await state.update_data(currency_name=currency)
    await message.answer("Введите курс этой валюты к рублю (например: 89.50):")
    await state.set_state(CurrencyStates.waiting_currency_rate)

@dp.message(CurrencyStates.waiting_currency_rate)
async def process_currency_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат. Введите положительное число:")
        return

    data = await state.get_data()
    currency_name = data['currency_name']
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CURRENCY_MANAGER_URL}/load",
            json={"currency_name": currency_name, "rate": rate}
        )
        
        if response.status_code != 200:
            await message.answer(f"❌ Ошибка при добавлении валюты: {response.json().get('detail', '')}")
            await state.clear()
            return

    is_admin = message.text == ADMIN_COMMAND
    menu = await get_inline_menu_keyboard(is_admin)
    await message.answer(f"✅ Валюта {currency_name} добавлена с курсом {rate} RUB.", reply_markup=menu)
    await state.clear()

# Удаление валюты
@dp.callback_query(F.data == "delete_currency")
async def cb_delete_currency(callback: CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DATA_MANAGER_URL}/currencies")
        if response.status_code != 200 or not response.json():
            await callback.message.answer("⚠️ Нет валют для удаления.")
            await callback.answer()
            return

        currencies = response.json()
        builder = InlineKeyboardBuilder()
        for currency in currencies:
            builder.button(text=currency["currency_name"], callback_data=f"delete_{currency['currency_name']}")
        builder.button(text="🔙 Назад", callback_data="manage_currency")
        builder.adjust(2)
        await callback.message.edit_text("Выберите валюту для удаления:", reply_markup=builder.as_markup())
        await callback.answer()

@dp.callback_query(F.data.startswith("delete_"))
async def cb_confirm_delete_currency(callback: CallbackQuery):
    currency_name = callback.data.split("_", 1)[1]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CURRENCY_MANAGER_URL}/delete",
            json={"currency_name": currency_name, "rate": 0}  # rate не используется при удалении
        )
        
        if response.status_code != 200:
            await callback.message.answer(f"❌ Ошибка при удалении валюты: {response.json().get('detail', '')}")
            await callback.answer()
            return

    is_admin = callback.message.text == ADMIN_COMMAND
    menu = await get_inline_menu_keyboard(is_admin)
    await callback.message.edit_text(f"✅ Валюта {currency_name} удалена.", reply_markup=menu)
    await callback.answer()

# Изменение курса валюты
@dp.callback_query(F.data == "change_rate")
async def cb_change_rate(callback: CallbackQuery):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DATA_MANAGER_URL}/currencies")
        if response.status_code != 200 or not response.json():
            await callback.message.answer("⚠️ Нет валют для изменения.")
            await callback.answer()
            return

        currencies = response.json()
        builder = InlineKeyboardBuilder()
        for currency in currencies:
            builder.button(text=currency["currency_name"], callback_data=f"change_{currency['currency_name']}")
        builder.button(text="🔙 Назад", callback_data="manage_currency")
        builder.adjust(2)
        await callback.message.edit_text("Выберите валюту для изменения курса:", reply_markup=builder.as_markup())
        await callback.answer()

@dp.callback_query(F.data.startswith("change_"))
async def cb_start_change_rate(callback: CallbackQuery, state: FSMContext):
    currency_name = callback.data.split("_", 1)[1]
    await state.update_data(currency_to_change=currency_name)
    await callback.message.answer(f"Введите новый курс для {currency_name}:")
    await state.set_state(CurrencyStates.waiting_new_rate)
    await callback.answer()

@dp.message(CurrencyStates.waiting_new_rate)
async def process_new_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат. Введите положительное число:")
        return

    data = await state.get_data()
    currency_name = data['currency_to_change']
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CURRENCY_MANAGER_URL}/update_currency",
            json={"currency_name": currency_name, "rate": rate}
        )
        
        if response.status_code != 200:
            await message.answer(f"❌ Ошибка при обновлении курса: {response.json().get('detail', '')}")
            await state.clear()
            return

    is_admin = message.text == ADMIN_COMMAND
    menu = await get_inline_menu_keyboard(is_admin)
    await message.answer(f"✅ Курс валюты {currency_name} обновлен: {rate} RUB.", reply_markup=menu)
    await state.clear()

# Запуск бота
async def main():
    await init_db()
    pool = await create_db_pool()
    dp["pool"] = pool
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())