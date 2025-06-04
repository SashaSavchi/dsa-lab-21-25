from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import pool
import logging
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Пул соединений с БД
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)

# Функция для получения соединения с базой данных из пула соединений
def get_db_connection():
    return db_pool.getconn()

# Функция для возврата соединения обратно в пул
def close_db_connection(conn):
    db_pool.putconn(conn)

# Функция для логирования входящих запросов
def log_request(action, currency_name=None, amount=None):
    logger.info(f"Request: {action}, Currency: {currency_name}, Amount: {amount}")

# Маршрут для конвертации валют
@app.route('/convert', methods=['GET'])
def convert_currency():
    # Получаем параметры из запроса
    currency_name = request.args.get('currency_name')
    amount = request.args.get('amount')

    # Логируем запрос
    log_request("CONVERT", currency_name, amount)
    
    # Пробуем преобразовать amount в число
    try:
        amount = float(amount)
    except ValueError:
        logger.warning(f"Invalid amount value: {amount}")
        return jsonify({"message": "Invalid amount value"}), 400

    conn = None
    try:
        # Получаем соединение с БД
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Ищем валюту в базе данных
            cursor.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
            existing_currency = cursor.fetchone()

            # Если валюта не найдена
            if not existing_currency:
                logger.warning(f"Currency not found: {currency_name}")
                return jsonify({"message": "Currency not found"}), 404

            # Выполняем конвертацию
            rate = existing_currency[0]
            converted_amount = amount * float(rate)
            logger.info(f"Conversion successful: {amount} {currency_name} = {converted_amount}")
            return jsonify({"converted_amount": converted_amount}), 200
    except psycopg2.Error as e:
        # Обработка ошибок базы данных
        logger.error(f"Database error in convert: {str(e)}")
        return jsonify({"message": f"Database error: {str(e)}"}), 500
    finally:
        # Всегда возвращаем соединение в пул
        if conn:
            close_db_connection(conn)

# Маршрут для получения списка всех валют
@app.route('/currencies', methods=['GET'])
def get_currencies():
    conn = None
    try:
        # Получаем соединение с БД
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Получаем список всех валют из базы
            cursor.execute("SELECT currency_name, rate FROM currencies ORDER BY currency_name")
            # Формируем список словарей с валютами и курсами
            currencies = [{"currency_name": row[0], "rate": float(row[1])} for row in cursor.fetchall()]
            logger.info(f"Retrieved {len(currencies)} currencies")
            return jsonify({"currencies": currencies}), 200
    except psycopg2.Error as e:
        # Обработка ошибок базы данных
        logger.error(f"Database error in get_currencies: {str(e)}")
        return jsonify({"message": f"Database error: {str(e)}"}), 500
    finally:
        # Всегда возвращаем соединение в пул
        if conn:
            close_db_connection(conn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)