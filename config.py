import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Validate required environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Количество правильных ответов, необходимых для перехода на следующий уровень Блума
# Индекс 0 не используется, так как уровни начинаются с 1
REQUIRED_CORRECT_ANSWERS = [
    0,  # Не используется
    5,  # Для перехода с уровня 1 на уровень 2 (Запоминание -> Понимание)
    4,  # Для перехода с уровня 2 на уровень 3 (Понимание -> Применение)
    3,  # Для перехода с уровня 3 на уровень 4 (Применение -> Анализ)
    3,  # Для перехода с уровня 4 на уровень 5 (Анализ -> Оценка)
    2   # Для перехода с уровня 5 на уровень 6 (Оценка -> Творчество)
]

# OpenAI prompt for lesson generation
LESSON_PROMPT = """Ты — преподаватель межславянского языка. Твоя задача — генерировать короткие обучающие задания в стиле микролёрнинга, подходящие для использования в Telegram-боте.

Каждое задание должно включать:

1. Краткое теоретическое объяснение (максимум 3–5 предложений) на русском языке. Объяснение должно касаться одного понятия: слово, корень, буква, грамматическая форма.
2. Один вопрос в формате викторины с 2–4 вариантами ответа на русском. Один из них должен быть правильным, остальные — правдоподобные, но ошибочные.
3. Укажи правильный вариант ответа для автоматической проверки.

Выводи результат в формате JSON:

{
  "lesson": "<объяснение>",
  "question": "<вопрос>",
  "options": ["А", "Б", "В", "Г"],
  "correct_answer": "Б"
}

Контент должен быть рассчитан на начинающих. Используй межславянские слова, корни, алфавит, церковные и исторические примеры. Объяснение и задание — **на русском языке**, но со вставками межславянских слов и форм."""
