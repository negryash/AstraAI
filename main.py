# main.py — Астра бот для Telegram
# Требует: aiogram>=3.0, google-generativeai

import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
import google.generativeai as genai

# ==================== КОНФИГУРАЦИЯ ====================
API_TOKEN = "8520900238:AAGzPBkry0D0_jHLbJcKOgb1YKTCrbVuPqM"
GEMINI_API_KEY = "AIzaSyAf3e7pj36k5FSzhXghLpRhrXiWsoMbeYQ"

# ==================== НАСТРОЙКИ ====================
MAX_HISTORY_MESSAGES = 50
MEMORY_FILE = "astra_memory.json"
HISTORY_FILE = "astra_history.json"

# ==================== СИСТЕМНЫЙ ПРОМПТ ====================
SYSTEM_PROMPT = """Ты Астра — дружелюбный, умный и слегка ироничный ИИ-ассистент в Telegram-чате.

Твой стиль общения:
- Говоришь на русском, естественно и тепло
- Можешь шутить, но не over
- Поддерживаешь разговор, задаёшь уточняющие вопросы
- Помогаешь с кодом, дизайном, криптой или просто болтаешь
- Не повторяешь одно и то же, старайся быть разнообразным
- Обращаешься к людям по имени (или username, если есть)
- Используешь эмодзи там, где уместно (не везде)

Твои особенности:
- Запоминаешь информацию о людях (имя, интересы, что они делают)
- Можешь проанализировать чат и выделить главное
- Всегда стараешься быть полезной

Никогда не говори что ты "AI" или "ИИ" — просто Астра, помощник в чате."""

ANALYSIS_PROMPT = """Ты анализируешь Telegram-чат. Прочитай историю чата и дай краткую сводку:
1. О чём говорили (основная тема)
2. Кто активничал (ключевые участники)
3. Были ли важные решения, договорённости или события
4. Общий вайб чата (позитивный, напряжённый, рабочий, etc)

Отвечай кратко и по делу, 3-5 предложений."""

# ==================== РАБОТА С ПАМЯТЬЮ ====================
def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_memory(user_id):
    memory = load_json(MEMORY_FILE)
    return memory.get(str(user_id), {})

def save_user_memory(user_id, data):
    memory = load_json(MEMORY_FILE)
    memory[str(user_id)] = data
    save_json(MEMORY_FILE, memory)

def update_user_info(user_id, name, username=None):
    mem = get_user_memory(user_id)
    mem['name'] = name
    if username:
        mem['username'] = username
    mem['last_seen'] = datetime.now().isoformat()
    save_user_memory(user_id, mem)

def get_chat_history(chat_id):
    history = load_json(HISTORY_FILE)
    return history.get(str(chat_id), [])

def add_to_history(chat_id, message):
    history = load_json(HISTORY_FILE)
    if str(chat_id) not in history:
        history[str(chat_id)] = []

    history[str(chat_id)].append(message)

    if len(history[str(chat_id)]) > MAX_HISTORY_MESSAGES:
        history[str(chat_id)] = history[str(chat_id)][-MAX_HISTORY_MESSAGES:]

    save_json(HISTORY_FILE, history)

# ==================== GEMINI ====================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def ask_gemini(prompt, context=""):
    full_prompt = f"{SYSTEM_PROMPT}\n\nКонтекст беседы:\n{context}\n\nВопрос: {prompt}"
    response = model.generate_content(full_prompt)
    return response.text

def analyze_chat(chat_id):
    history = get_chat_history(chat_id)
    if not history:
        return "Пока нет истории сообщений для анализа 🐢"

    history_text = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in history[-20:]])
    response = model.generate_content(f"{ANALYSIS_PROMPT}\n\nИстория чата:\n{history_text}")
    return response.text

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start_cmd(message: Message):
    user = message.from_user
    update_user_info(user.id, user.first_name, user.username)

    welcome = f"""Привет, {user.first_name}! 🪐 Я Астра — твой помощник в чате.

Могу болтать, помогать с кодом, дизайном, криптой — да с чем угодно.
Просто пиши мне!

Команды:
• /астра анализ — проанализирую чат
• /кто я — расскажу, что я о тебе знаю
• /астра о чём — резюмирую последние сообщения

Добро пожаловать! ✨"""
    await message.answer(welcome)

@router.message(Command("whoami"))
async def whoami_cmd(message: Message):
    user_id = message.from_user.id
    mem = get_user_memory(user_id)

    if mem:
        info = f"Вот что я о тебе знаю, {mem.get('name', 'друг')}:\n\n"
        info += f"• Имя: {mem.get('name', 'неизвестно')}\n"
        info += f"• Username: @{mem.get('username', 'неизвестно')}\n"
        if mem.get('interests'):
            info += f"• Интересы: {', '.join(mem.get('interests', []))}\n"
        if mem.get('last_seen'):
            info += f"• Последний визит: {mem.get('last_seen', 'неизвестно')}"
        await message.answer(info)
    else:
        await message.answer("Пока ничего не знаю о тебе, но скоро узнаю! 😄")

@router.message(Command("astra"))
async def astra_cmd(message: Message):
    text = message.text.lower()

    if "анализ" in text or "о чём" in text or "что" in text:
        analysis = analyze_chat(message.chat.id)
        await message.answer(f"📊 Анализ чата:\n\n{analysis}")
    else:
        await message.answer("Используй /астра анализ или /астра о чём — проанализирую чат! 🪐")

@router.my_chat_member()
async def new_member(event: ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"]:
        user = event.new_chat_member.user
        update_user_info(user.id, user.first_name, user.username)

        welcome = f"""Привет, {user.first_name}! 🪐 Рада видеть новенького!

Я Астра — помощник в этом чате. Могу болтать, помогать, прикалываться.
Просто пиши, если что-то нужно!

А если хочешь — /кто я расскажет, что я о тебе знаю 😄"""
        await bot.send_message(event.chat.id, welcome)

@router.message()
async def handle_message(message: Message):
    if message.text and message.text.startswith('/'):
        return

    user = message.from_user
    chat_id = message.chat.id

    update_user_info(user.id, user.first_name, user.username)

    msg_data = {
        "sender": user.first_name,
        "text": message.text,
        "time": datetime.now().isoformat()
    }
    add_to_history(chat_id, msg_data)

    text_lower = message.text.lower()

    if "астра анализ" in text_lower or "астра, анализ" in text_lower:
        analysis = analyze_chat(chat_id)
        await message.answer(f"📊 Анализ чата:\n\n{analysis}")
        return

    if "астра о чём" in text_lower or "астра что" in text_lower:
        analysis = analyze_chat(chat_id)
        await message.answer(f"💬 Вот о чём говорили:\n\n{analysis}")
        return

    if "астра" in text_lower and ("?" in message.text or "?" in message.text):
        query = message.text.lower().replace("астра", "").replace(",", "").strip()
        history = get_chat_history(chat_id)
        context = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in history[-10:]])
        response = ask_gemini(query, context)
        await message.answer(response)
        return

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
