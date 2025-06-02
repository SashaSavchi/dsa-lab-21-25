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

# Функция для получения соединения из пула
def get_connection():
    return db_pool.getconn()

# Функция для возврата соединения в пул
def return_connection(conn):
    db_pool.putconn(conn)

# Функция для логирования запросов
def log_request(action, currency_name=None, rate=None):
    logger.info(f"Request: {action}, Currency: {currency_name}, Rate: {rate}")

# Маршрут для загрузки новой валюты
@app.route('/load', methods=['POST'])
def load_currency():
    conn = get_connection()  # Получаем соединение с БД
    try:
        data = request.get_json()  # Получаем JSON данные из запроса
        currency_name = data.get('currency_name')  # Извлекаем название валюты
        rate = data.get('rate')  # Извлекаем курс валюты
        
        log_request("LOAD", currency_name, rate)  # Логируем запрос
        
        # # Проверяем наличие обязательных полей
        # if not currency_name or not rate:
        #     logger.warning("Invalid JSON data received")
        #     return jsonify({"message": "Invalid JSON data"}), 400

        with conn.cursor() as cursor:
            # Проверяем, существует ли уже такая валюта
            cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
            if cursor.fetchone():
                logger.warning(f"Currency already exists: {currency_name}")
                return jsonify({"message": "Currency already exists"}), 400

            # Добавляем новую валюту в БД
            cursor.execute("INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)", (currency_name, rate))
            conn.commit()  # Подтверждаем изменения
            logger.info(f"Currency loaded successfully: {currency_name}")
            return jsonify({"message": "Currency loaded successfully"}), 200
    except Exception as e:
        conn.rollback()  # Откатываем изменения в случае ошибки
        logger.error(f"Error in load_currency: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
    finally:
        return_connection(conn)  # Всегда возвращаем соединение в пул

# Маршрут для обновления курса валюты
@app.route('/update_currency', methods=['POST'])
def update_currency():
    conn = get_connection()  # Получаем соединение с БД
    try:
        data = request.get_json()  # Получаем JSON данные из запроса
        currency_name = data.get('currency_name')  # Извлекаем название валюты
        new_rate = data.get('rate')  # Извлекаем новый курс
        
        log_request("UPDATE", currency_name, new_rate)  # Логируем запрос
        
        # # Проверяем наличие обязательных полей
        # if not currency_name or not new_rate:
        #     logger.warning("Invalid JSON data received")
        #     return jsonify({"message": "Invalid JSON data"}), 400

        with conn.cursor() as cursor:
            # Проверяем, существует ли валюта
            cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
            if not cursor.fetchone():
                logger.warning(f"Currency not found: {currency_name}")
                return jsonify({"message": "Currency not found"}), 404

            # Обновляем курс валюты
            cursor.execute("UPDATE currencies SET rate = %s WHERE currency_name = %s", (new_rate, currency_name))
            conn.commit()  # Подтверждаем изменения
            logger.info(f"Currency updated successfully: {currency_name}")
            return jsonify({"message": "Currency updated successfully"}), 200
    except Exception as e:
        conn.rollback()  # Откатываем изменения в случае ошибки
        logger.error(f"Error in update_currency: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
    finally:
        return_connection(conn)  # Всегда возвращаем соединение в пул

# Маршрут для удаления валюты
@app.route('/delete', methods=['POST'])
def delete_currency():
    conn = get_connection()  # Получаем соединение с БД
    try:
        data = request.get_json()  # Получаем JSON данные из запроса
        currency_name = data.get('currency_name')  # Извлекаем название валюты
        
        log_request("DELETE", currency_name)  # Логируем запрос
        
        # Проверяем наличие обязательного поля
        # if not currency_name:
        #     logger.warning("Invalid JSON data received")
        #     return jsonify({"message": "Invalid JSON data"}), 400

        with conn.cursor() as cursor:
            # Проверяем, существует ли валюта
            cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
            if not cursor.fetchone():
                logger.warning(f"Currency not found: {currency_name}")
                return jsonify({"message": "Currency not found"}), 404

            # Удаляем валюту из БД
            cursor.execute("DELETE FROM currencies WHERE currency_name = %s", (currency_name,))
            conn.commit()  # Подтверждаем изменения
            logger.info(f"Currency deleted successfully: {currency_name}")
            return jsonify({"message": "Currency deleted successfully"}), 200
    except Exception as e:
        conn.rollback()  # Откатываем изменения в случае ошибки
        logger.error(f"Error in delete_currency: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
    finally:
        return_connection(conn)  # Всегда возвращаем соединение в пул

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)