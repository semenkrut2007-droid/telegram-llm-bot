import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import Router
from openai import OpenAI
from aiogram.client.session.aiohttp import AiohttpSession
import asyncio

# Загружаем переменные окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PROXY_URL = os.getenv("PROXY_URL")

# Настройка клиента OpenRouter для доступа к LLM
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://t.me/vvit05_bot",
        "X-Title": "Telegram LLM Bot",
    }
)

# Настройка сессии с SOCKS5-прокси для обхода блокировок
if PROXY_URL:
    logger.info(f"Использую прокси: {PROXY_URL}")
    session = AiohttpSession(proxy=PROXY_URL)
else:
    session = None

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN, session=session)
dp = Dispatcher()
router = Router()

# Хранилище истории диалогов (контекст до 10 сообщений)
dialogue_history = {}

# Системный промпт для LLM
SYSTEM_PROMPT = """Ты полезный ассистент в Telegram.
Отвечай дружелюбно и информативно. Используй форматирование Markdown для улучшения читаемости."""

async def get_llm_response(user_id: int, user_message: str) -> str:
    """Отправляет запрос к LLM через OpenRouter и возвращает ответ"""
    try:
        if user_id not in dialogue_history:
            dialogue_history[user_id] = []
        
        dialogue_history[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *dialogue_history[user_id][-10:]  # Контекст: последние 10 сообщений
        ]
        
        try:
            completion = client.chat.completions.create(
                model="google/gemini-2.0-flash-exp:free",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            response = completion.choices[0].message.content
            
            dialogue_history[user_id].append({
                "role": "assistant",
                "content": response
            })
            
            return response

        except Exception as api_error:
            logger.error(f"Ошибка OpenRouter API: {api_error}")
            return f"❌ Ошибка модели: {type(api_error).__name__} - {api_error}"

    except Exception as e:
        logger.error(f"Общая ошибка: {e}")
        return f"❌ Общая ошибка: {type(e).__name__} - {e}"

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
👋 **Привет! Я бот с искусственным интеллектом.**

Я использую модель Gemini 2.0 от Google через OpenRouter API.

Я могу:
- Отвечать на ваши вопросы
- Помогать с программированием
- Переводить тексты
- И многое другое!

Просто напишите мне сообщение, и я отвечу!

Доступные команды:
/start - Показать это сообщение
/help - Получить помощь
/clear - Очистить историю диалога
"""
    await message.answer(welcome_text, parse_mode="Markdown")

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
📚 **Справка по использованию бота**

Бот использует искусственный интеллект для ответов на ваши сообщения.

**Как использовать:**
• Просто отправьте текстовое сообщение
• Бот запомнит контекст диалога (последние 10 сообщений)
• Используйте /clear чтобы начать новый диалог

**Рекомендации:**
• Задавайте четкие и конкретные вопросы
• Можно просить написать код, перевести текст, объяснить концепцию
"""
    await message.answer(help_text, parse_mode="Markdown")

# Обработчик команды /clear
@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_id = message.from_user.id
    if user_id in dialogue_history:
        dialogue_history[user_id] = []
    await message.answer("✅ История диалога очищена!")

# Обработчик текстовых сообщений
@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Индикатор "печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Получаем ответ от LLM
    response = await get_llm_response(user_id, message.text)
    
    # Отправляем ответ
    try:
        await message.answer(response, parse_mode="Markdown")
    except:
        # Если Markdown ломается — отправляем без форматирования
        await message.answer(response)

# Точка входа
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
