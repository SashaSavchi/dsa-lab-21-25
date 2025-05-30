from fastapi import FastAPI, HTTPException
import asyncpg
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()
print("Connecting with user:", os.getenv("DB_USER"))

# Конфигурация базы данных
DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
}

async def get_db_connection():
    return await asyncpg.connect(**DB_CONFIG)

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

class ConvertInput(BaseModel):
    currency_name: str
    amount: float


@app.get("/convert")
async def convert_currency(currency_name: str, amount: float):
    conn = await get_db_connection()
    try:
        rate = await conn.fetchval(
            "SELECT rate FROM currencies WHERE currency_name = $1", 
            currency_name
        )
        if rate is None:
            raise HTTPException(status_code=404, detail="Валюта не найдена")
        
        result = amount * rate
        return {"converted_amount": result}
    finally:
        await conn.close()


@app.get("/currencies")
async def get_all_currencies():
    conn = await get_db_connection()
    try:
        currencies = await conn.fetch(
            "SELECT currency_name, rate FROM currencies ORDER BY currency_name"
        )
        return [dict(currency) for currency in currencies]
    finally:
        await conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)