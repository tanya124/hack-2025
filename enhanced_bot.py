#!/usr/bin/env python3

import asyncio
import json
import logging
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, logger
from openai_service import openai_service
from database import db
import httpx

class OldChurchSlavonicBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = httpx.AsyncClient(timeout=60.0)
        self.quiz_sessions = {}
        self.user_states = {}  # Track user onboarding state
    
    async def send_message(self, chat_id, text, reply_markup=None):
        """Send a message to a chat"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        try:
            response = await self.session.post(f"{self.base_url}/sendMessage", data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {"ok": False}
    
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
        
        try:
            response = await self.session.post(f"{self.base_url}/editMessageText", data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return {"ok": False}
    
    async def answer_callback_query(self, callback_query_id, text=None):
        """Answer a callback query"""
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        
        try:
            response = await self.session.post(f"{self.base_url}/answerCallbackQuery", data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")
            return {"ok": False}
    
    async def get_updates(self, offset=None):
        """Get updates from Telegram"""
        params = {"timeout": 10}  # Reduced timeout
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
        """Handle /start command with intro message"""
        user_id = user['id']
        username = user.get('username')
        first_name = user.get('first_name', 'друг')
        
        # Save user to database
        db.save_user(user_id, username, first_name)
        
        # Check if user is already onboarded
        existing_user = db.get_user(user_id)
        if existing_user and existing_user.get('level') and existing_user.get('goal'):
            await self.show_main_menu(chat_id, first_name)
            return
        
        # Show intro message
        intro_message = (
            f"Радуйся, {first_name}!\n\n"
            "Ты вступил во врата Бота-Словѣса — хранителя древняго глагола и премудрости старых времен.\n"
            "Аще взыщеши познания о слове древнем и писменех стары, — ты обрёл верный путь.\n\n"
            "Азъ есмь спутник твой, наставник и глас глаголицы.\n"
            "Слово откроется тебе — по мере сердца и усердия твоего.\n\n"
            "⚔️ Да начнем путь учения!"
        )
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "Дальше →",
                "callback_data": "next_intro"
            }]]
        }
        
        await self.send_message(chat_id, intro_message, keyboard)
    
    async def handle_level_selection(self, chat_id, message_id):
        """Handle level selection step"""
        level_message = (
            "Во истину, всякому учению начало подобает.\n"
            "Скажи ж мне, другъ, в каковей степени пребываешь ты в премудрости словенской?\n\n"
            "🔸 **Азъ есмь начатый**\n"
            "– Лишь ведаю буквы, но жажду смысла.\n\n"
            "🔸 **Вѣдѣю понемногу**\n"
            "– Читал малое, разумѣю кое-что, но хочу углубити разумъ.\n\n"
            "🔸 **Старецъ словесный**\n"
            "– Много прочёл, но и ныне ищу глубинъ новых.\n\n"
            "Избери, да воздам ти путь соответный."
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔸 Азъ есмь начатый", "callback_data": "level_beginner"}],
                [{"text": "🔸 Вѣдѣю понемногу", "callback_data": "level_intermediate"}],
                [{"text": "🔸 Старецъ словесный", "callback_data": "level_advanced"}]
            ]
        }
        
        await self.edit_message(chat_id, message_id, level_message, keyboard)
    
    async def handle_goal_selection(self, chat_id, message_id, level):
        """Handle goal selection step"""
        goal_message = (
            "Каждое учение по плоду познаётся.\n"
            "Скажи ж, какова есть цель странствия твоего в слове древнем?\n\n"
            "⚖️ **Хощу разумѣти тексты**\n"
            "– Да чту Евангелие, летописи и молитвы с разумѣнием.\n\n"
            "🎙️ **Желаю глаголати**\n"
            "– Да говорю во образ древних, яко инокъ или витязь на вече.\n\n"
            "🎭 **Интересъ мой — ритуалъ и образъ**\n"
            "– Ищю словесъ для чаров, песнопений, тайнодействий.\n\n"
            "🪶 **Ищу вдохновения**\n"
            "– Слово древнее мне — какъ огнь в груди и пища душе.\n\n"
            "Избери путь — и в том пути да наставлю тя."
        )
        
        # Store level in user state temporarily
        self.user_states[chat_id] = {'level': level}
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "⚖️ Хощу разумѣти тексты", "callback_data": "goal_texts"}],
                [{"text": "🎙️ Желаю глаголати", "callback_data": "goal_speaking"}],
                [{"text": "🎭 Интересъ мой — ритуалъ и образъ", "callback_data": "goal_ritual"}],
                [{"text": "🪶 Ищу вдохновения", "callback_data": "goal_inspiration"}]
            ]
        }
        
        await self.edit_message(chat_id, message_id, goal_message, keyboard)
    
    async def complete_onboarding(self, chat_id, message_id, goal, user_id):
        """Complete onboarding and show main menu"""
        # Get stored level from user state
        level = self.user_states.get(chat_id, {}).get('level', 'beginner')
        
        # Save to database
        db.save_user(user_id, level=level, goal=goal)
        
        # Clean up user state
        if chat_id in self.user_states:
            del self.user_states[chat_id]
        
        # Get user's first name for personalized response
        user_data = db.get_user(user_id)
        first_name = user_data.get('first_name', 'друг') if user_data else 'друг'
        
        await self.show_main_menu(chat_id, first_name, message_id)
    
    async def show_main_menu(self, chat_id, first_name, message_id=None):
        """Show main menu with options"""
        main_message = (
            f"Добро пожаловать, {first_name}!\n\n"
            "Путь твой определён. Что желаешь сотворити?\n\n"
            "📖 **Получить задание** — новый урок и испытание\n"
            "📜 **Посмотреть прогресс** — летопись твоих достижений"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                [{"text": "📜 Посмотреть прогресс", "callback_data": "show_progress"}]
            ]
        }
        
        if message_id:
            await self.edit_message(chat_id, message_id, main_message, keyboard)
        else:
            await self.send_message(chat_id, main_message, keyboard)
    
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
                'answered': False,
                'chat_id': chat_id,
                'message_id': message_id
            }
            
            # Format message
            message = f"📚 **Урок по старославянскому языку**\n\n"
            message += f"{lesson_data['lesson']}\n\n"
            message += f"❓ **Вопрос:**\n{lesson_data['question']}"
            
            # Create keyboard with options
            keyboard = {"inline_keyboard": []}
            for i, option in enumerate(lesson_data['options']):
                keyboard["inline_keyboard"].append([{
                    "text": option,
                    "callback_data": f"answer_{i}_{option[:20]}"  # Truncate for callback limit
                }])
            
            await self.edit_message(chat_id, message_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error generating assignment: {e}")
            error_keyboard = {
                "inline_keyboard": [
                    [{"text": "📖 Попробовать снова", "callback_data": "get_assignment"}],
                    [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                ]
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
            option_index = int(parts[1])
            user_answer = session['options'][option_index]  # Get full answer from session
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
        
        # Format result - SEND NEW MESSAGE instead of editing
        if is_correct:
            result = "✅ **Правильно!**"
        else:
            result = f"❌ **Неправильно.**\n🎯 Правильный ответ: **{session['correct_answer']}**"
        
        result_message = f"{result}\n\n"
        if feedback:
            result_message += f"💡 {feedback}\n\n"
        result_message += "Что желаешь делать дальше?"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                [{"text": "📜 Посмотреть прогресс", "callback_data": "show_progress"}]
            ]
        }
        
        # Send new message instead of editing
        await self.send_message(chat_id, result_message, keyboard)
        
        # Save progress to database
        db.save_progress(
            user_id=user_id,
            lesson_topic="Урок старославянского",
            question=session['question'],
            user_answer=user_answer,
            correct_answer=session['correct_answer'],
            is_correct=is_correct
        )
        
        # Clean up session
        del self.quiz_sessions[user_id]
        logger.info(f"User {user_id} answered {'correctly' if is_correct else 'incorrectly'}")
    
    async def show_progress(self, chat_id, message_id, user_id):
        """Show user progress as a chronicle"""
        user_data = db.get_user(user_id)
        stats = db.get_user_stats(user_id)
        progress_history = db.get_user_progress(user_id)
        
        if not user_data:
            await self.edit_message(chat_id, message_id, "Ошибка: пользователь не найден.")
            return
        
        first_name = user_data.get('first_name', 'Странник')
        
        # Generate chronicle using current date in Old Church Slavonic style
        current_year = datetime.now().year
        byzantine_year = current_year + 5508  # Byzantine calendar
        month_name = datetime.now().strftime("%B")
        day = datetime.now().day
        
        # Russian month names in old style
        month_names = {
            "January": "января", "February": "февраля", "March": "марта",
            "April": "апреля", "May": "мая", "June": "июня",
            "July": "июля", "August": "августа", "September": "сентября",
            "October": "октября", "November": "ноября", "December": "декабря"
        }
        
        chronicle = f"📜 **Летопись ученого инока {first_name}**\n\n"
        chronicle += f"В лето {byzantine_year} ({current_year} от Р.Х.), месяца {month_names.get(month_name, month_name)} {day} дня...\n\n"
        
        # Add statistics
        total = stats.get('total_lessons', 0)
        correct = stats.get('correct_answers', 0)
        accuracy = (correct / total * 100) if total > 0 else 0
        
        chronicle += f"**Статистика подвигов:**\n"
        chronicle += f"• Уроков пройдено: {total}\n"
        chronicle += f"• Правильных ответов: {correct}\n"
        chronicle += f"• Точность знания: {accuracy:.1f}%\n"
        chronicle += f"• Дней в учении: {stats.get('days_active', 0)}\n\n"
        
        if progress_history:
            chronicle += "**Последние деяния:**\n"
            for i, record in enumerate(progress_history[:5], 1):
                status = "✅" if record['is_correct'] else "❌"
                date_str = record['completed_at'].strftime("%d.%m")
                chronicle += f"{i}. {date_str} - {status} {record['lesson_topic'][:30]}...\n"
        else:
            chronicle += "Ещё не было подвигов в учении. Начни свой путь!"
        
        chronicle += f"\n*Аще тако преуспеет {first_name}, и будет ему даровано знание глаголицы...*"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
            ]
        }
        
        await self.edit_message(chat_id, message_id, chronicle, keyboard)
    
    async def run(self):
        """Main bot loop"""
        logger.info("Starting Enhanced Old Church Slavonic Bot...")
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
                            
                            if text in ["/start", "/help"]:
                                await self.handle_start_command(chat_id, user)
                        
                        # Handle callback queries
                        elif "callback_query" in update:
                            query = update["callback_query"]
                            chat_id = query["message"]["chat"]["id"]
                            message_id = query["message"]["message_id"]
                            user_id = query["from"]["id"]
                            data = query["data"]
                            
                            await self.answer_callback_query(query["id"])
                            
                            # Handle different callback types
                            if data == "next_intro":
                                await self.handle_level_selection(chat_id, message_id)
                            elif data.startswith("level_"):
                                level = data.replace("level_", "")
                                await self.handle_goal_selection(chat_id, message_id, level)
                            elif data.startswith("goal_"):
                                goal = data.replace("goal_", "")
                                await self.complete_onboarding(chat_id, message_id, goal, user_id)
                            elif data == "get_assignment":
                                await self.handle_get_assignment(chat_id, message_id, user_id)
                            elif data.startswith("answer_"):
                                await self.handle_quiz_answer(chat_id, message_id, user_id, data)
                            elif data == "show_progress":
                                await self.show_progress(chat_id, message_id, user_id)
                            elif data == "main_menu":
                                user_data = db.get_user(user_id)
                                first_name = user_data.get('first_name', 'друг') if user_data else 'друг'
                                await self.show_main_menu(chat_id, first_name, message_id)
                
                await asyncio.sleep(2)  # Increased sleep time
                
            except Exception as e:
                logger.error(f"Error in bot loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Longer sleep on error

async def main():
    bot = OldChurchSlavonicBot(TELEGRAM_BOT_TOKEN)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())