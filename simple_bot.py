#!/usr/bin/env python3

import asyncio
import json
import logging
from config import TELEGRAM_BOT_TOKEN, logger
from openai_service import openai_service

# Simple bot implementation using direct HTTP requests to Telegram API
import httpx

class SimpleTelegramBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = httpx.AsyncClient()
        self.quiz_sessions = {}
    
    async def send_message(self, chat_id, text, reply_markup=None):
        """Send a message to a chat"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        response = await self.session.post(f"{self.base_url}/sendMessage", data=data)
        return response.json()
    
    async def edit_message(self, chat_id, message_id, text, reply_markup=None):
        """Edit a message"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        response = await self.session.post(f"{self.base_url}/editMessageText", data=data)
        return response.json()
    
    async def answer_callback_query(self, callback_query_id, text=None):
        """Answer a callback query"""
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        
        response = await self.session.post(f"{self.base_url}/answerCallbackQuery", data=data)
        return response.json()
    
    async def get_updates(self, offset=None):
        """Get updates from Telegram"""
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        
        try:
            response = await self.session.get(f"{self.base_url}/getUpdates", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
            return {"ok": False, "error": str(e)}
    
    async def handle_start_command(self, chat_id, user):
        """Handle /start command"""
        welcome_message = (
            f"Добро пожаловать, {user.get('first_name', 'друг')}! 👋\n\n"
            "🏛️ **Бот для изучения межславянского языка**\n\n"
            "Здесь вы изучите основы межславянского языка через короткие уроки "
            "и интерактивные задания. Каждый урок содержит теоретическое объяснение "
            "и вопрос для закрепления материала.\n\n"
            "Нажмите кнопку ниже, чтобы получить первое задание!"
        )
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "📖 Получить задание",
                "callback_data": "get_assignment"
            }]]
        }
        
        await self.send_message(chat_id, welcome_message, keyboard)
    
    async def handle_get_assignment(self, chat_id, message_id, user_id):
        """Handle get assignment request"""
        # Clear any existing session
        if user_id in self.quiz_sessions:
            del self.quiz_sessions[user_id]
        
        # Show loading message
        await self.edit_message(chat_id, message_id, "⏳ Генерируем новое задание...")
        
        try:
            # Generate lesson and quiz
            lesson_data = await openai_service.generate_lesson_and_quiz()
            
            # Store session
            self.quiz_sessions[user_id] = {
                'lesson': lesson_data['lesson'],
                'question': lesson_data['question'],
                'options': lesson_data['options'],
                'correct_answer': lesson_data['correct_answer'],
                'answered': False
            }
            
            # Format message
            message = f"📚 **Урок по межславянскому языку**\n\n"
            message += f"{lesson_data['lesson']}\n\n"
            message += f"❓ **Вопрос:**\n{lesson_data['question']}"
            
            # Create keyboard with options
            keyboard = {"inline_keyboard": []}
            for i, option in enumerate(lesson_data['options']):
                keyboard["inline_keyboard"].append([{
                    "text": option,
                    "callback_data": f"answer_{i}_{option}"
                }])
            
            await self.edit_message(chat_id, message_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error generating assignment: {e}")
            error_keyboard = {
                "inline_keyboard": [[{
                    "text": "📖 Попробовать снова",
                    "callback_data": "get_assignment"
                }]]
            }
            await self.edit_message(
                chat_id, message_id, 
                f"😔 Ошибка при создании задания: {str(e)}", 
                error_keyboard
            )
    
    async def handle_quiz_answer(self, chat_id, message_id, user_id, callback_data):
        """Handle quiz answer"""
        session = self.quiz_sessions.get(user_id)
        if not session or session['answered']:
            return
        
        # Parse answer
        try:
            parts = callback_data.split("_", 2)
            user_answer = parts[2]
        except:
            return
        
        session['answered'] = True
        session['user_answer'] = user_answer
        is_correct = user_answer == session['correct_answer']
        
        # Show loading
        await self.edit_message(chat_id, message_id, "⏳ Проверяем ответ...")
        
        try:
            # Generate feedback
            feedback = await openai_service.generate_feedback(
                session['question'], user_answer, session['correct_answer'], is_correct
            )
        except:
            feedback = None
        
        # Format result
        if is_correct:
            result = "✅ **Правильно!**"
        else:
            result = f"❌ **Неправильно.**\n🎯 Правильный ответ: **{session['correct_answer']}**"
        
        message = f"{result}\n\n"
        if feedback:
            message += f"💡 {feedback}\n\n"
        message += "Нажмите «Получить задание» для нового урока!"
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "📖 Получить задание",
                "callback_data": "get_assignment"
            }]]
        }
        
        await self.edit_message(chat_id, message_id, message, keyboard)
        
        # Clean up session
        del self.quiz_sessions[user_id]
        logger.info(f"User {user_id} answered {'correctly' if is_correct else 'incorrectly'}")
    
    async def run(self):
        """Main bot loop"""
        logger.info("Starting Simple Telegram Bot...")
        offset = None
        
        while True:
            try:
                updates = await self.get_updates(offset)
                
                if updates.get("ok"):
                    for update in updates.get("result", []):
                        offset = update["update_id"] + 1
                        
                        # Handle messages
                        if "message" in update:
                            message = update["message"]
                            chat_id = message["chat"]["id"]
                            user = message["from"]
                            text = message.get("text", "")
                            
                            if text == "/start":
                                await self.handle_start_command(chat_id, user)
                            elif text == "/help":
                                await self.handle_start_command(chat_id, user)
                        
                        # Handle callback queries
                        elif "callback_query" in update:
                            query = update["callback_query"]
                            chat_id = query["message"]["chat"]["id"]
                            message_id = query["message"]["message_id"]
                            user_id = query["from"]["id"]
                            data = query["data"]
                            
                            await self.answer_callback_query(query["id"])
                            
                            if data == "get_assignment":
                                await self.handle_get_assignment(chat_id, message_id, user_id)
                            elif data.startswith("answer_"):
                                await self.handle_quiz_answer(chat_id, message_id, user_id, data)
                else:
                    logger.error(f"Failed to get updates: {updates}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in bot loop: {e}", exc_info=True)
                await asyncio.sleep(5)

async def main():
    bot = SimpleTelegramBot(TELEGRAM_BOT_TOKEN)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())