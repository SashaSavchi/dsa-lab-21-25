import os
import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
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

# Инициализация бота и хранилища
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage) 

# Хранение курсов валют
currencies = {}

# Состояния FSM
class CurrencyStates(StatesGroup):
    waiting_currency_name = State()
    waiting_currency_rate = State()
    waiting_convert_currency = State()
    waiting_convert_amount = State()

# Функция для создания меню
def get_main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="/save_currency"),
        types.KeyboardButton(text="/convert"),
        types.KeyboardButton(text="/list")
    )
    return builder.as_markup(resize_keyboard=True)


# Функция для валидации валюты
def validate_currency(currency: str) -> bool:
    """Проверяет, что введена валюта только из английских букв (3 символа)"""
    return bool(re.fullmatch(r'^[A-Za-z]{3}$', currency))


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "💱 Бот для конвертации валют\n\n"
        "Доступные команды:\n"
        "/save_currency - сохранить курс валюты\n"
        "/convert - конвертировать в рубли\n"
        "/list - показать все курсы",
        reply_markup=get_main_menu_keyboard()
    )


# Обработчик для отмены любой команды
@dp.message(lambda message: message.text.lower() in ["отмена", "стоп", "cancel", "выход", "начать"])
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await cmd_start(message)


# Обработчик команды /save_currency
@dp.message(Command("save_currency"))
async def cmd_save_currency(message: types.Message, state: FSMContext):
    await state.set_state(CurrencyStates.waiting_currency_name)
    await message.answer(
        "Введите название валюты (например: USD):",
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(CurrencyStates.waiting_currency_name)
async def process_currency_name(message: types.Message, state: FSMContext):
    currency = message.text.upper()
    if not validate_currency(currency):
        await message.answer("❌ Неверный формат валюты! Введите 3 английские буквы (например: USD):")
    else:
        await state.update_data(currency=currency)
        await state.set_state(CurrencyStates.waiting_currency_rate)
        await message.answer(f"Введите курс для {currency} к RUB (например: 85.8):")

@dp.message(CurrencyStates.waiting_currency_rate)
async def process_currency_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
        if rate <= 0:
            raise ValueError
            
        data = await state.get_data()
        currency = data['currency']
        currencies[currency] = rate
        
        await state.clear()
        await message.answer(
            f"✅ Курс {currency} сохранен: 1 {currency} = {rate} RUB",
            reply_markup=get_main_menu_keyboard()
        )
    except ValueError:
        await message.answer("❌ Ошибка! Введите число в правильном формате:")


# Обработчик команды /convert
@dp.message(Command("convert"))
async def cmd_convert(message: types.Message, state: FSMContext):
    if not currencies:
        await message.answer(
            "🔹 Нет сохраненных валют. Сначала используйте /save_currency",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await state.set_state(CurrencyStates.waiting_convert_currency)
    await message.answer(
        "Введите название валюты для конвертации (например: USD):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(CurrencyStates.waiting_convert_currency)
async def process_convert_currency(message: types.Message, state: FSMContext):
    currency = message.text.upper()
    if not validate_currency(currency):
        await message.answer("❌ Неверный формат валюты! Введите 3 английские буквы (например: USD):")
    
    elif currency not in currencies:
        await message.answer(f"❌ Валюта {currency} не найдена! Попробуйте снова:")
    else:
        await state.update_data(currency=currency)
        await state.set_state(CurrencyStates.waiting_convert_amount)
        await message.answer(f"Введите сумму в {currency} для конвертации в RUB:")

@dp.message(CurrencyStates.waiting_convert_amount)
async def process_convert_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
            
        data = await state.get_data()
        currency = data['currency']
        rate = currencies[currency]
        result = amount * rate
        
        await state.clear()
        await message.answer(
            f"Результат конвертации:\n"
            f"{amount} {currency} = {result:.2f} RUB\n"
            f"Курс: 1 {currency} = {rate} RUB",
            reply_markup=get_main_menu_keyboard()
        )
    except ValueError:
        await message.answer("❌ Ошибка! Введите положительное число:")


# Обработчик команды /list
@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    if not currencies:
        await message.answer(
            "❗ Нет сохраненных валют",
            reply_markup=get_main_menu_keyboard()
        )
    else:
    
        # Создаем инлайн-клавиатуру для удаления
        builder = InlineKeyboardBuilder()
        for currency in currencies.keys():
            builder.button(text=f"❌ Удалить {currency}", callback_data=f"delete_{currency}")
        builder.adjust(1)  # По одной кнопке в строке
        
        response = "Сохраненные курсы:\n" + "\n".join(
            f"- {currency}: {rate} RUB" for currency, rate in currencies.items()
        )
        
        await message.answer(
            response,
            reply_markup=builder.as_markup()
        )


# Обработчик нажатий на кнопки удаления
@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def process_delete_currency(callback: types.CallbackQuery):
    currency = callback.data.split("_")[1]
    
    if currency in currencies:
        del currencies[currency]
        await callback.message.edit_text(
            f"✅ Валюта {currency} удалена",
            reply_markup=None
        )


# Обработчик любых других сообщений
@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer(
        "Пожалуйста, используйте меню или команды:\n"
        "/save_currency - сохранить курс валюты\n"
        "/convert - конвертировать в рубли\n"
        "/list - показать все курсы",
        reply_markup=get_main_menu_keyboard()
    )


async def main():
    await dp.start_polling(bot, skip_updates=True)

asyncio.run(main())