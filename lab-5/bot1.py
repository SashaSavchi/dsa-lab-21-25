import asyncio
import asyncpg
import re
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from dotenv import load_dotenv
from decimal import Decimal

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

# Обработчик отмены состояния
@dp.message(lambda message: message.text.lower() in ["отмена", "стоп", "cancel", "выход", "начать"])
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await cmd_start(message)

# Получение курсов валют
@dp.callback_query(F.data == "get_currencies")
async def cb_get_currencies(callback: CallbackQuery):
    pool = dp["pool"]
    async with pool.acquire() as conn:
        currencies = await conn.fetch("SELECT currency_name, rate FROM currencies ORDER BY currency_name")
        admin = await conn.fetchrow("SELECT * FROM admins WHERE chat_id = $1", str(callback.message.chat.id))
    is_admin = admin is not None
    menu = await get_inline_menu_keyboard(is_admin)

    if currencies:
        response = "Текущие курсы валют к рублю:\n" + "\n".join(
            f"- {currency['currency_name']}: {currency['rate']} RUB"
            for currency in currencies
        )
    else:
        response = "ℹ️ В базе данных нет сохраненных валют"

    await callback.message.edit_text(response, reply_markup=menu)
    await callback.answer()

# Начало конвертации
@dp.callback_query(F.data == "convert")
async def cb_convert(callback: CallbackQuery, state: FSMContext):
    pool = dp["pool"]
    async with pool.acquire() as conn:
        currencies = await conn.fetch("SELECT currency_name FROM currencies")

    if not currencies:
        await callback.message.answer("ℹ️ В базе нет валют для конвертации")
        await callback.answer()
        return

    await callback.message.answer("💸 Введите название валюты для конвертации (например: USD):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CurrencyStates.waiting_convert_currency)
    await callback.answer()

# Получение кода валюты для конвертации
@dp.message(CurrencyStates.waiting_convert_currency)
async def process_convert_currency(message: types.Message, state: FSMContext):
    currency = message.text.strip().upper()
    pool = dp["pool"]

    if not validate_currency(currency):
        await message.answer("❌ Неверный формат валюты! Введите 3 английские буквы (например: USD):")
        return

    async with pool.acquire() as conn:
        currency_data = await conn.fetchrow("SELECT rate FROM currencies WHERE currency_name = $1", currency)

    if currency_data is None:
        await message.answer(f"❌ Валюта {currency} не найдена! Попробуйте снова:")
        return

    await state.update_data(currency=currency, rate=currency_data['rate'])
    await message.answer(f"Введите сумму в {currency} для конвертации в RUB:")
    await state.set_state(CurrencyStates.waiting_convert_amount)

# Конвертация суммы
@dp.message(CurrencyStates.waiting_convert_amount)
async def process_convert_amount(message: types.Message, state: FSMContext):
    pool = dp["pool"]
    try:
        amount = Decimal(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError

        data = await state.get_data()
        currency = data['currency']
        rate = data['rate']
        result = amount * rate
        await state.clear()

        async with pool.acquire() as conn:
            admin = await conn.fetchrow("SELECT * FROM admins WHERE chat_id = $1", str(message.chat.id))
        is_admin = admin is not None
        menu = await get_inline_menu_keyboard(is_admin)

        await message.answer(
            f"Результат конвертации:\n"
            f"{amount} {currency} = {result:.2f} RUB\n"
            f"Курс: 1 {currency} = {rate} RUB",
            reply_markup=menu
        )
    except ValueError:
        await message.answer("❌ Ошибка! Введите положительное число:")

# Вход в админку
@dp.message(lambda message: message.text == ADMIN_COMMAND)
async def become_admin(message: Message):
    pool = dp["pool"]
    chat_id = str(message.chat.id)
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM admins WHERE chat_id = $1", chat_id)
        if not exists:
            await conn.execute("INSERT INTO admins (chat_id) VALUES ($1)", chat_id)
            await message.answer("✅ Вы стали администратором!")
        else:
            await message.answer("ℹ️ Вы уже являетесь администратором.")
    await cmd_start(message)

# Выход из админки
@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery):
    pool = dp["pool"]
    chat_id = str(callback.message.chat.id)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE chat_id = $1", chat_id)
    menu = await get_inline_menu_keyboard(False)
    await callback.message.edit_text("📋 Вы вышли из админки.", reply_markup=menu)
    await callback.answer()


# Добавление валюты
@dp.callback_query(F.data == "add_currency")
async def cb_add_currency(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код новой валюты (например: USD):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CurrencyStates.waiting_currency_name)
    await callback.answer()

# Проверка и ввод новой валюты
@dp.message(CurrencyStates.waiting_currency_name)
async def process_currency_name(message: types.Message, state: FSMContext):
    currency = message.text.strip().upper()
    if not validate_currency(currency):
        await message.answer("❌ Неверный формат валюты. Введите 3 английские буквы:")
        return

    pool = dp["pool"]
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM currencies WHERE currency_name = $1", currency)
    if exists:
        await message.answer(f"❌ Валюта {currency} уже существует. Введите другой код:")
        return

    await state.update_data(currency_name=currency)
    await message.answer("Введите курс этой валюты к рублю (например: 89.50):")
    await state.set_state(CurrencyStates.waiting_currency_rate)

# Добавление валюты в базу
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
    pool = dp["pool"]
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO currencies (currency_name, rate) VALUES ($1, $2)", currency_name, rate)
        admin = await conn.fetchrow("SELECT * FROM admins WHERE chat_id = $1", str(message.chat.id))
    is_admin = admin is not None
    menu = await get_inline_menu_keyboard(is_admin)

    await message.answer(f"✅ Валюта {currency_name} добавлена с курсом {rate} RUB.", reply_markup=menu)
    await state.clear()

# Удаление валюты
@dp.callback_query(F.data == "delete_currency")
async def cb_delete_currency(callback: CallbackQuery):
    pool = dp["pool"]
    async with pool.acquire() as conn:
        currencies = await conn.fetch("SELECT currency_name FROM currencies")

    if not currencies:
        await callback.message.answer("⚠️ Нет валют для удаления.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for currency in currencies:
        builder.button(text=currency["currency_name"], callback_data=f"delete_{currency['currency_name']}")
    builder.button(text="🔙 Назад", callback_data="manage_currency")
    builder.adjust(2)
    await callback.message.edit_text("Выберите валюту для удаления:", reply_markup=builder.as_markup())
    await callback.answer()

# Подтверждение удаления
@dp.callback_query(F.data.startswith("delete_"))
async def cb_confirm_delete_currency(callback: CallbackQuery):
    currency_name = callback.data.split("_", 1)[1]
    pool = dp["pool"]
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM currencies WHERE currency_name = $1", currency_name)
        admin = await conn.fetchrow("SELECT * FROM admins WHERE chat_id = $1", str(callback.message.chat.id))
    is_admin = admin is not None
    menu = await get_inline_menu_keyboard(is_admin)

    await callback.message.edit_text(f"✅ Валюта {currency_name} удалена.", reply_markup=menu)
    await callback.answer()
    

# Управление валютами
@dp.callback_query(F.data == "manage_currency")
async def cb_manage_currency(callback: CallbackQuery):
    menu = await get_currency_management_keyboard()
    await callback.message.edit_text("🛠 Управление валютами:", reply_markup=menu)
    await callback.answer()


# Изменение курса валюты
@dp.callback_query(F.data == "change_rate")
async def cb_change_rate(callback: CallbackQuery):
    pool = dp["pool"]
    async with pool.acquire() as conn:
        currencies = await conn.fetch("SELECT currency_name FROM currencies")

    if not currencies:
        await callback.message.answer("⚠️ Нет валют для изменения.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for currency in currencies:
        builder.button(text=currency["currency_name"], callback_data=f"change_{currency['currency_name']}")
    builder.button(text="🔙 Назад", callback_data="manage_currency")
    builder.adjust(2)
    await callback.message.edit_text("Выберите валюту для изменения курса:", reply_markup=builder.as_markup())
    await callback.answer()

# Ввод нового курса
@dp.callback_query(F.data.startswith("change_"))
async def cb_start_change_rate(callback: CallbackQuery, state: FSMContext):
    currency_name = callback.data.split("_", 1)[1]
    await state.update_data(currency_to_change=currency_name)
    await callback.message.answer(f"Введите новый курс для {currency_name}:")
    await state.set_state(CurrencyStates.waiting_new_rate)  # Используем новое состояние
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
    pool = dp["pool"]
    async with pool.acquire() as conn:
        await conn.execute("UPDATE currencies SET rate = $1 WHERE currency_name = $2", rate, currency_name)
        admin = await conn.fetchrow("SELECT * FROM admins WHERE chat_id = $1", str(message.chat.id))
    is_admin = admin is not None
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
