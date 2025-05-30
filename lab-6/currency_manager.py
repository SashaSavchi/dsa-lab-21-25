from fastapi import FastAPI, HTTPException
import asyncpg
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

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

class CurrencyInput(BaseModel):
    currency_name: str
    rate: float

@app.post("/load")
async def load_currency(currency_data: CurrencyInput):
    async with await get_db_connection() as conn:
        # Проверка существования валюты
        exists = await conn.fetchval(
            "SELECT 1 FROM currencies WHERE currency_name = $1", 
            currency_data.currency_name
        )
        if exists:
            raise HTTPException(status_code=400, detail="Валюта уже существует")
        
        # Добавление валюты
        await conn.execute(
            "INSERT INTO currencies (currency_name, rate) VALUES ($1, $2)",
            currency_data.currency_name, currency_data.rate
        )
    return {"status": "OK"}

@app.post("/update_currency")
async def update_currency(currency_data: CurrencyInput):
    async with await get_db_connection() as conn:
        # Проверка существования валюты
        exists = await conn.fetchval(
            "SELECT 1 FROM currencies WHERE currency_name = $1", 
            currency_data.currency_name
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Валюта не найдена")
        
        # Обновление курса
        await conn.execute(
            "UPDATE currencies SET rate = $1 WHERE currency_name = $2",
            currency_data.rate, currency_data.currency_name
        )
    return {"status": "OK"}

@app.post("/delete")
async def delete_currency(currency_data: CurrencyInput):
    async with await get_db_connection() as conn:
        # Проверка существования валюты
        exists = await conn.fetchval(
            "SELECT 1 FROM currencies WHERE currency_name = $1", 
            currency_data.currency_name
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Валюта не найдена")
        
        # Удаление валюты
        await conn.execute(
            "DELETE FROM currencies WHERE currency_name = $1",
            currency_data.currency_name
        )
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)