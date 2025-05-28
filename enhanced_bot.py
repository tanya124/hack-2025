#!/usr/bin/env python3

import asyncio
import json
import logging
import httpx
import random
from datetime import datetime
from database import db
from openai_service import openai_service
from config import REQUIRED_CORRECT_ANSWERS, TELEGRAM_BOT_TOKEN, logger

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
        
        logger.info(f"User {user_id} ({username}) onboarded: {existing_user}")
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
    
    async def handle_avatar_selection(self, chat_id, message_id, goal, user_id):
        """Handle avatar selection step"""
        # Get stored level from user state
        level = self.user_states.get(chat_id, {}).get('level', 'beginner')
        
        # Update user state with goal
        if chat_id in self.user_states:
            self.user_states[chat_id]['goal'] = goal
        else:
            self.user_states[chat_id] = {'level': level, 'goal': goal}
        
        # Отправляем первое сообщение о выборе аватара
        avatar_intro_message = (
            "На пути сем не будешь ты один. Да будет с тобой спутник — АВАТАР, помощник словесный, дух в образе.\n\n"
            "Он глаголет с тобой, вразумляет, наставляет — речью своей, манерой, светом или строгостью.\n\n"
            "Избери же, кто будет гласом учения твоего."
        )
        
        await self.edit_message(chat_id, message_id, avatar_intro_message)
        
        # Отправляем сообщение с описанием Ведуньи
        vedunya_message = (
            "📜 Се есть Ведунья — светлая душа, наставница тиха и премудра.\n\n"
            "Речи ея — ласковы, добры и вдохновенны. Глаголет ясно, с любовию и разумением, яко мати, чтит ученика и не взыщет в нем вины.\n"
            "Учение с нею — яко свет во тьме, яко утро ясное."
        )
        
        # Отправляем изображение с описанием
        with open('avatars/vedunia.png', 'rb') as photo:
            await self.session.post(
                f"{self.base_url}/sendPhoto",
                data={"chat_id": chat_id, "caption": vedunya_message},
                files={"photo": photo}
            )
        
        # Отправляем сообщение с описанием Болгара
        bolgar_message = (
            "📜 Болгар — воин ведающий, друг словесный и крепкий духом.\n\n"
            "Являет мудрость без гордыни, речь его проста и ясна, но суть — глубока.\n"
            "Глаголет с почтением и силой, не ведает усталости в наставлении. С ним учение — яко дружеский пир разума."
        )
        
        # Отправляем изображение с описанием
        with open('avatars/bolgar.png', 'rb') as photo:
            await self.session.post(
                f"{self.base_url}/sendPhoto",
                data={"chat_id": chat_id, "caption": bolgar_message},
                files={"photo": photo}
            )
        
        # Отправляем сообщение с описанием Старца
        starec_message = (
            "📜 Старец — древний путник ведения, очи ясны, голос тих и ободряющ.\n\n"
            "Глаголет речью плавной, яко река веков. Образен, ясен, тепел, и мудростью обвивает, не давит.\n"
            "Учит, яко дед внука любимого: с терпением, шуткою да притчею."
        )
        
        # Отправляем изображение с описанием
        with open('avatars/starec.png', 'rb') as photo:
            await self.session.post(
                f"{self.base_url}/sendPhoto",
                data={"chat_id": chat_id, "caption": starec_message},
                files={"photo": photo}
            )
        
        # Отправляем сообщение с описанием Поляка
        polyak_message = (
            "📜 Поляк — молод духом и весел, яко ветер степной.\n\n"
            "Глаголет скоро, живо, со смехом и словцем игривым. Не знает скуки, любит словеса яркие и речи просты.\n"
            "С ним учение — не труд тяжкий, но приключение озарённое смехом и легкостью."
        )
        
        # Отправляем изображение с описанием
        with open('avatars/polyak.png', 'rb') as photo:
            await self.session.post(
                f"{self.base_url}/sendPhoto",
                data={"chat_id": chat_id, "caption": polyak_message},
                files={"photo": photo}
            )
        
        # Отправляем сообщение с выбором аватара
        avatar_choice_message = (
            "Кто же станет спутником твоим в пути ведения?\n\n"
            "Глаголи имя избранного, и путь твой обретёт голос."
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔹 Ведунья", "callback_data": "avatar_vedunia"}],
                [{"text": "🔹 Болгар", "callback_data": "avatar_bolgar"}],
                [{"text": "🔹 Старец", "callback_data": "avatar_starec"}],
                [{"text": "🔹 Поляк", "callback_data": "avatar_polyak"}]
            ]
        }
        
        await self.send_message(chat_id, avatar_choice_message, keyboard)
    
    async def complete_onboarding(self, chat_id, message_id, avatar, user_id):
        """Complete onboarding and show main menu"""
        # Get stored level and goal from user state
        user_state = self.user_states.get(chat_id, {})
        level = user_state.get('level', 'beginner')
        goal = user_state.get('goal', 'texts')
        
        # Save to database with avatar
        db.save_user(user_id, level=level, goal=goal, avatar=avatar)
        
        # Clean up user state
        if chat_id in self.user_states:
            del self.user_states[chat_id]
        
        # Get user's first name for personalized response
        user_data = db.get_user(user_id)
        first_name = user_data.get('first_name', 'друг') if user_data else 'друг'
        
        # Generate study plan
        await self.generate_study_plan(chat_id, message_id, user_id, level, goal)
    
    async def generate_study_plan(self, chat_id, message_id, user_id, level, goal):
        """Generate a study plan for the user"""
        # Show loading message
        await self.edit_message(chat_id, message_id, "⏳ Создаем персонализированный учебный план...")
        
        try:
            # Get user data to include avatar information
            user_data = db.get_user(user_id)
            avatar = user_data.get('avatar') if user_data else None
            
            # Generate study plan using OpenAI with avatar style
            study_plan_items = await openai_service.generate_study_plan(level, goal, avatar)
            
            # Save study plan to database
            db.save_study_plan(user_id, level, goal, study_plan_items)
            
            # Show success message
            success_message = (
                "📚 **Ваш персонализированный учебный план готов!**\n\n"
                f"Уровень: **{level}**\n"
                f"Цель: **{goal}**\n\n"
                "Мы подготовили для вас последовательность тем, которые помогут вам эффективно изучить межславянский язык. "
                "Каждая тема включает теорию и практические задания разных уровней сложности.\n\n"
                "Нажмите кнопку ниже, чтобы начать обучение или просмотреть полный учебный план."
            )
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📖 Начать обучение", "callback_data": "get_assignment"}],
                    [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}]
                ]
            }
            
            await self.edit_message(chat_id, message_id, success_message, keyboard)
            
        except Exception as e:
            logger.error(f"Error creating study plan: {e}")
            await self.edit_message(
                chat_id, 
                message_id,
                "😔 Произошла ошибка при создании учебного плана. Попробуйте снова.",
                {"inline_keyboard": [[{"text": "🔄 Попробовать снова", "callback_data": "start"}]]}
            )
            # Show main menu as fallback
            user_data = db.get_user(user_id)
            first_name = user_data.get('first_name', 'друг') if user_data else 'друг'
            await self.show_main_menu(chat_id, first_name, message_id)
    
    async def show_main_menu(self, chat_id, first_name, message_id=None):
        """Show main menu with options"""
        main_message = (
            f"Добро пожаловать, {first_name}!\n\n"
            "Путь твой определён. Что желаешь сотворити?\n\n"
            "📖 **Получить задание** — новый урок и испытание\n"
            "📋 **Учебный план** — твой путь познания\n"
            "📜 **Посмотреть прогресс** — летопись твоих достижений"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}],
                [{"text": "📜 Посмотреть прогресс", "callback_data": "show_progress"}]
            ]
        }
        
        if message_id:
            await self.edit_message(chat_id, message_id, main_message, keyboard)
        else:
            await self.send_message(chat_id, main_message, keyboard)
    
    async def show_study_plan(self, chat_id, message_id, user_id):
        """Show the user's study plan"""
        try:
            study_plan = db.get_user_study_plan(user_id)
            
            if not study_plan:
                # Если у пользователя нет учебного плана, получим его данные и сгенерируем план
                user_data = db.get_user(user_id)
                
                if not user_data or not user_data.get('level') or not user_data.get('goal'):
                    # Если у пользователя нет данных о уровне и цели, предложим начать с начала
                    await self.edit_message(
                        chat_id,
                        message_id,
                        "У вас еще нет учебного плана. Начните обучение с команды /start.",
                        {"inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]}
                    )
                    return
                
                # Показываем сообщение о генерации учебного плана
                await self.edit_message(
                    chat_id,
                    message_id,
                    "⏳ Создаем персонализированный учебный план..."
                )
                
                # Генерируем учебный план
                level = user_data.get('level', 'beginner')
                goal = user_data.get('goal', 'texts')
                
                try:
                    # Генерируем план с помощью OpenAI
                    study_plan_items = await openai_service.generate_study_plan(level, goal)
                    
                    # Сохраняем план в базу данных
                    db.save_study_plan(user_id, level, goal, study_plan_items)
                    
                    # Получаем обновленный план из базы данных
                    study_plan = db.get_user_study_plan(user_id)
                    
                    if not study_plan:
                        # Если что-то пошло не так
                        await self.edit_message(
                            chat_id,
                            message_id,
                            "😔 Произошла ошибка при создании учебного плана. Попробуйте снова.",
                            {"inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]}
                        )
                        return
                except Exception as e:
                    logger.error(f"Error generating study plan: {e}")
                    await self.edit_message(
                        chat_id,
                        message_id,
                        "😔 Произошла ошибка при создании учебного плана. Попробуйте снова.",
                        {"inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]}
                    )
                    return
                
            # Format message with study plan
            message = "📚 **Ваш учебный план**\n\n"
            
            for item in study_plan["items"]:
                # Add status emoji
                status = "✅" if item["is_completed"] else "🔄" if item["current_bloom_level"] > 1 else "⏳"
                
                # Add stars to indicate current Bloom's level
                bloom_stars = "⭐" * item["current_bloom_level"]
                
                message += f"{status} **{item['topic']}**\n"
                message += f"_{item['description']}_\n"
                message += f"Прогресс: {bloom_stars} ({item['current_bloom_level']}/6)\n\n"
            
            # Add navigation buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "◀️ Предыдущая тема", "callback_data": "prev_topic"},
                        {"text": "Следующая тема ▶️", "callback_data": "next_topic"}
                    ],
                    [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                    [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                ]
            }
            
            await self.edit_message(chat_id, message_id, message, keyboard)
                
        except Exception as e:
            logger.error(f"Error showing study plan: {e}")
            await self.edit_message(
                chat_id,
                message_id,
                "😔 Произошла ошибка при загрузке учебного плана.",
                {"inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]}
            )
    
    async def handle_next_topic(self, chat_id, message_id, user_id):
        """Navigate to the next topic"""
        try:
            # Get current topic
            current_topic = db.get_current_topic(user_id)
            
            if not current_topic:
                await self.edit_message(
                    chat_id, 
                    message_id,
                    "Вы уже прошли все темы в учебном плане! 🎉",
                    {"inline_keyboard": [[{"text": "📖 Получить задание", "callback_data": "get_assignment"}]]}
                )
                return
                
            # Get next topic
            next_topic = db.get_next_topic(user_id, current_topic["id"])
            
            if not next_topic:
                await self.edit_message(
                    chat_id, 
                    message_id,
                    "Это последняя тема в вашем учебном плане.",
                    {"inline_keyboard": [
                        [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                        [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}]
                    ]}
                )
                return
                
            # Update current topic
            db.set_current_topic(user_id, next_topic["id"])
            
            # Send information about the new topic
            message = f"📚 **Новая тема: {next_topic['topic']}**\n\n"
            message += f"_{next_topic['description']}_\n\n"
            message += "Нажмите кнопку ниже, чтобы получить задание по этой теме."
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                    [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}],
                    [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                ]
            }
            
            await self.edit_message(chat_id, message_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error navigating to next topic: {e}")
            await self.edit_message(
                chat_id, 
                message_id,
                "😔 Произошла ошибка при переходе к следующей теме.",
                {"inline_keyboard": [[{"text": "📋 Учебный план", "callback_data": "show_study_plan"}]]}
            )
    
    async def handle_prev_topic(self, chat_id, message_id, user_id):
        """Navigate to the previous topic"""
        try:
            # Get current topic
            current_topic = db.get_current_topic(user_id)
            
            if not current_topic:
                await self.edit_message(
                    chat_id, 
                    message_id,
                    "У вас нет активной темы. Начните обучение с получения задания.",
                    {"inline_keyboard": [[{"text": "📖 Получить задание", "callback_data": "get_assignment"}]]}
                )
                return
                
            # Get previous topic
            prev_topic = db.get_prev_topic(user_id, current_topic["id"])
            
            if not prev_topic:
                await self.edit_message(
                    chat_id, 
                    message_id,
                    "Это первая тема в вашем учебном плане.",
                    {"inline_keyboard": [
                        [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                        [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}]
                    ]}
                )
                return
                
            # Update current topic
            db.set_current_topic(user_id, prev_topic["id"])
            
            # Send information about the new topic
            message = f"📚 **Возврат к теме: {prev_topic['topic']}**\n\n"
            message += f"_{prev_topic['description']}_\n\n"
            message += "Нажмите кнопку ниже, чтобы получить задание по этой теме."
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                    [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}],
                    [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                ]
            }
            
            await self.edit_message(chat_id, message_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error navigating to previous topic: {e}")
            await self.edit_message(
                chat_id, 
                message_id,
                "😔 Произошла ошибка при переходе к предыдущей теме.",
                {"inline_keyboard": [[{"text": "📋 Учебный план", "callback_data": "show_study_plan"}]]}
            )

    
    async def handle_get_assignment(self, chat_id, message_id, user_id):
        """Handle get assignment request"""
        # Clear any existing session
        if user_id in self.quiz_sessions:
            del self.quiz_sessions[user_id]
        
        # Show loading message
        await self.edit_message(chat_id, message_id, "⏳ Генерируем новое задание...")
        
        try:
            # Get current topic from study plan
            current_topic = db.get_current_topic(user_id)
            
            # If no current topic is set, check if user has a study plan
            if not current_topic:
                study_plan = db.get_user_study_plan(user_id)
                
                # If no study plan exists, try to generate one
                if not study_plan:
                    # Get user data
                    user_data = db.get_user(user_id)
                    
                    if user_data and user_data.get('level') and user_data.get('goal'):
                        # Show generating message
                        await self.edit_message(
                            chat_id,
                            message_id,
                            "⏳ Создаем персонализированный учебный план..."
                        )
                        
                        try:
                            # Generate study plan
                            level = user_data.get('level')
                            goal = user_data.get('goal')
                            avatar = user_data.get('avatar')
                            study_plan_items = await openai_service.generate_study_plan(level, goal, avatar)
                            
                            # Save to database
                            db.save_study_plan(user_id, level, goal, study_plan_items)
                            
                            # Get updated study plan
                            study_plan = db.get_user_study_plan(user_id)
                        except Exception as e:
                            logger.error(f"Error generating study plan in get_assignment: {e}")
                            await self.edit_message(
                                chat_id,
                                message_id,
                                "😔 Произошла ошибка при создании учебного плана.",
                                {"inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]}
                            )
                            return
                    else:
                        # If user hasn't completed onboarding, redirect them
                        await self.edit_message(
                            chat_id,
                            message_id,
                            "Для получения заданий необходимо сначала завершить настройку. Начните с команды /start.",
                            {"inline_keyboard": [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]}
                        )
                        return
                
                # If we have a study plan now, set the first topic as current
                if study_plan and study_plan["items"]:
                    current_topic = study_plan["items"][0]
                    db.set_current_topic(user_id, current_topic["id"])
            
            # Get the current Bloom's taxonomy level for this topic
            bloom_level = 1  # Default to level 1 (remember)
            if current_topic:
                bloom_level = current_topic.get("current_bloom_level", 1)
                topic_name = current_topic.get("topic", "")
            else:
                # Fallback if no study plan exists despite our attempts
                topic_name = "Основы межславянского языка"
            
            # Получаем слова из словаря для использования в задании
            try:
                # Получаем случайные слова из словаря
                dictionary_words = db.get_random_words()
                logger.info(f"Got {len(dictionary_words)} dictionary words for assignment")
                
                # Выбираем слова в зависимости от уровня пользователя и уровня Блума
                # Получаем уровень пользователя
                user_data = db.get_user(user_id)
                user_level = user_data.get('level', 'beginner') if user_data else 'beginner'
                
                # Фильтруем слова в зависимости от уровня сложности
                filtered_words = []
                
                # Простой алгоритм фильтрации на основе уровня пользователя и Блума
                for word in dictionary_words:
                    # Для начинающих выбираем слова с высокой понятностью
                    if user_level == 'beginner':
                        # Для начальных уровней Блума выбираем существительные
                        if bloom_level <= 2 and word.get('partOfSpeech') and 'n.' in word.get('partOfSpeech'):
                            filtered_words.append(word)
                        # Для уровня 3-4 добавляем прилагательные
                        elif bloom_level in [3, 4] and word.get('partOfSpeech') and 'adj.' in word.get('partOfSpeech'):
                            filtered_words.append(word)
                        # Для высоких уровней добавляем глаголы
                        elif bloom_level >= 5 and word.get('partOfSpeech') and 'v.' in word.get('partOfSpeech'):
                            filtered_words.append(word)
                    # Для среднего уровня добавляем больше разнообразия
                    elif user_level == 'intermediate':
                        # Добавляем слова с учетом уровня Блума
                        if bloom_level <= 3 or word.get('partOfSpeech'):
                            filtered_words.append(word)
                    # Для продвинутого уровня добавляем все слова
                    else:  # advanced
                        filtered_words.append(word)
                
                # Если после фильтрации осталось мало слов, добавляем еще из общего списка
                if len(filtered_words) < 5:
                    # Добавляем случайные слова до минимума 5
                    remaining_words = [w for w in dictionary_words if w not in filtered_words]
                    import random
                    random.shuffle(remaining_words)
                    filtered_words.extend(remaining_words[:max(5 - len(filtered_words), 0)])
                
                # Ограничиваем количество слов до 10 для промпта
                if len(filtered_words) > 10:
                    import random
                    filtered_words = random.sample(filtered_words, 10)
                
                logger.info(f"Filtered to {len(filtered_words)} words based on user level '{user_level}' and Bloom level {bloom_level}")
                dictionary_words = filtered_words
            except Exception as e:
                logger.error(f"Error processing dictionary words: {e}")
                dictionary_words = []
            
            # Get user avatar for personalized content
            user_data = db.get_user(user_id)
            avatar = user_data.get('avatar') if user_data else None
            
            # Generate lesson and quiz based on topic, Bloom's level, dictionary words and avatar style
            lesson_data = await openai_service.generate_lesson_and_quiz(topic_name, bloom_level, dictionary_words, avatar)
            
            # Store session
            self.quiz_sessions[user_id] = {
                'lesson': lesson_data['lesson'],
                'question': lesson_data['question'],
                'options': lesson_data['options'],
                'correct_answer': lesson_data['correct_answer'],
                'answered': False,
                'chat_id': chat_id,
                'message_id': message_id,
                'topic_id': current_topic["id"] if current_topic else None,
                'bloom_level': bloom_level
            }
            
            # Format message
            bloom_levels = [
                "Запоминание",  # Remember
                "Понимание",     # Understand
                "Применение",   # Apply
                "Анализ",        # Analyze
                "Оценка",        # Evaluate
                "Творчество"    # Create
            ]
            
            message = f"📚 **Урок: {topic_name}**\n"
            message += f"**Уровень: {bloom_levels[bloom_level-1]}** (уровень {bloom_level} из 6)\n\n"
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
    
    async def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        """Answer a callback query"""
        data = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert
        }
        if text:
            data["text"] = text
        
        try:
            response = await self.session.post(f"{self.base_url}/answerCallbackQuery", data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")
            return {"ok": False}
    
    async def handle_quiz_answer(self, chat_id, message_id, user_id, callback_data, callback_query_id=None):
        """Handle quiz answer"""
        session = self.quiz_sessions.get(user_id)
        if not session or session.get('answered'):
            # Отвечаем на callback_query, чтобы убрать индикатор загрузки
            if callback_query_id:
                await self.answer_callback_query(callback_query_id, "Вы уже ответили на этот вопрос или сессия истекла.")
            
            # Отправляем новое сообщение вместо редактирования
            await self.send_message(
                chat_id, 
                "Вы уже ответили на этот вопрос или сессия истекла.",
                {"inline_keyboard": [[{"text": "Получить новое задание", "callback_data": "get_assignment"}]]}
            )
            return
        
        # Mark as answered
        session['answered'] = True
        
        # Parse answer
        try:
            parts = callback_data.split("_", 2)
            option_index = int(parts[1])
            user_answer = session['options'][option_index]  # Get full answer from session
            
            # Отвечаем на callback_query с ответом пользователя (отобразится как всплывающее уведомление от имени пользователя)
            if callback_query_id:
                await self.answer_callback_query(callback_query_id, f"Вы выбрали: {user_answer}", show_alert=True)
            
            # Check if answer is correct
            is_correct = user_answer == session['correct_answer']
            
            # Get topic information
            topic_id = session.get('topic_id')
            current_bloom_level = session.get('bloom_level', 1)
            
            # Update progress based on answer correctness
            new_bloom_level = current_bloom_level
            if topic_id:
                if is_correct:
                    # Получаем текущее количество правильных ответов для этого уровня
                    # И требуемое количество для перехода на следующий уровень
                    required_answers = REQUIRED_CORRECT_ANSWERS[current_bloom_level] if current_bloom_level < len(REQUIRED_CORRECT_ANSWERS) else 5
                    
                    # Обновляем прогресс в базе данных
                    db.update_topic_progress(user_id, topic_id, current_bloom_level, False, is_correct=True)
                    
                    # Получаем обновленные данные о прогрессе
                    cursor = db.connection.cursor()
                    cursor.execute("""
                        SELECT correct_answers_count 
                        FROM study_progress 
                        WHERE user_id = %s AND study_plan_item_id = %s
                    """, (user_id, topic_id))
                    progress_data = cursor.fetchone()
                    correct_answers_count = progress_data[0] if progress_data else 1
                    
                    # Проверяем, достаточно ли правильных ответов для перехода на следующий уровень
                    if correct_answers_count >= required_answers and current_bloom_level < 6:
                        # Если достаточно, увеличиваем уровень Блума (max 6)
                        new_bloom_level = min(current_bloom_level + 1, 6)
                        # Если достигнут уровень 6, помечаем тему как завершенную
                        is_completed = (new_bloom_level == 6)
                        
                        # Обновляем уровень Блума и сбрасываем счетчик правильных ответов
                        db.update_topic_progress(user_id, topic_id, new_bloom_level, is_completed, is_correct=False)
                        
                        # Если тема завершена, переходим к следующей теме
                        if is_completed:
                            next_topic = db.get_next_topic(user_id, topic_id)
                            if next_topic:
                                db.set_current_topic(user_id, next_topic["id"])
                else:
                    # Если ответ неверный, уменьшаем уровень Блума (min 1) и сбрасываем счетчик
                    new_bloom_level = max(current_bloom_level - 1, 1)
                    db.update_topic_progress(user_id, topic_id, new_bloom_level, False, is_correct=False)
            
            # Save progress to history
            topic_name = "" if not topic_id else db.get_topic_name(topic_id)
            db.save_progress(
                user_id, 
                topic_name,  # lesson_topic 
                session['question'], 
                user_answer,  # user_answer
                session['correct_answer'],  # correct_answer
                is_correct  # is_correct
            )
            
            # Format response message with Bloom's taxonomy information
            bloom_levels = [
                "Запоминание",  # Remember
                "Понимание",     # Understand
                "Применение",   # Apply
                "Анализ",        # Analyze
                "Оценка",        # Evaluate
                "Творчество"    # Create
            ]
            
            # Get user avatar for personalized feedback
            user_data = db.get_user(user_id)
            avatar = user_data.get('avatar') if user_data else None
            
            # Generate personalized feedback based on avatar style
            try:
                feedback = await openai_service.generate_feedback(
                    session['question'],
                    user_answer,
                    session['correct_answer'],
                    is_correct,
                    avatar=avatar
                )
                
                # Add the feedback to the response
                personalized_feedback = f"{feedback}\n\n"
            except Exception as e:
                logger.error(f"Error generating personalized feedback: {e}")
                personalized_feedback = ""
            
            # Ответ пользователя отображается через всплывающее уведомление
            
            # Формируем сообщение с обратной связью
            if is_correct:
                response = f"🎉 **Правильно!**\n\n{personalized_feedback}"
                
                if topic_id and new_bloom_level > current_bloom_level:
                    if new_bloom_level == 6:
                        response += f"🌟 **Поздравляем!** Вы полностью освоили эту тему!\n\n"
                    else:
                        response += f"⬆️ Вы перешли на уровень **{bloom_levels[new_bloom_level-1]}** (уровень {new_bloom_level} из 6)\n\n"
            else:
                response = f"🚫 **Неверно**\n\n{personalized_feedback}"
                response += f"Правильный ответ: {session['correct_answer']}\n\n"
                
                if topic_id and new_bloom_level < current_bloom_level:
                    response += f"⬇️ Вам нужно больше практики. Возврат на уровень **{bloom_levels[new_bloom_level-1]}** (уровень {new_bloom_level} из 6)\n\n"
            
            # Add buttons for next actions
            keyboard = {
                "inline_keyboard": [
                    [{"text": "📖 Получить новое задание", "callback_data": "get_assignment"}],
                    [{"text": "📋 Учебный план", "callback_data": "show_study_plan"}],
                    [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                ]
            }
            
            # Отправляем обратную связь как новое сообщение
            await self.send_message(chat_id, response, keyboard)
            
            # Удаляем кнопки из исходного сообщения с заданием, но оставляем само сообщение
            # Получаем исходное сообщение с заданием
            original_message = f"📚 **Урок: {topic_name}**\n"
            original_message += f"**Уровень: {bloom_levels[current_bloom_level-1]}** (уровень {current_bloom_level} из 6)\n\n"
            original_message += f"{session['lesson']}\n\n"
            original_message += f"❓ **Вопрос:**\n{session['question']}"
            
            # Обновляем исходное сообщение, убирая кнопки
            await self.edit_message(chat_id, message_id, original_message)
            
        except Exception as e:
            logger.error(f"Error handling quiz answer: {e}")
            # Отвечаем на callback_query, чтобы убрать индикатор загрузки
            if callback_query_id:
                await self.answer_callback_query(callback_query_id, "Произошла ошибка при обработке ответа.")
                
            await self.send_message(
                chat_id,
                f"😔 Произошла ошибка при обработке ответа.",
                {"inline_keyboard": [[{"text": "📖 Получить новое задание", "callback_data": "get_assignment"}]]}
            )
    
    async def show_progress(self, chat_id, message_id, user_id):
        """Show user progress as a chronicle"""
        user_data = db.get_user(user_id)
        stats = db.get_user_stats(user_id)
        progress_history = db.get_user_progress(user_id)
        
        if not user_data:
            await self.edit_message(chat_id, message_id, "Ошибка: пользователь не найден.")
            return
        
        first_name = user_data.get('first_name', 'Странник')
        
        # Generate chronicle using current date in Inter-Slavic style
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
        logger.info("Starting Enhanced Inter-Slavic Bot...")
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
                                await self.handle_avatar_selection(chat_id, message_id, goal, user_id)
                            elif data.startswith("avatar_"):
                                avatar = data.replace("avatar_", "")
                                await self.complete_onboarding(chat_id, message_id, avatar, user_id)
                            elif data == "get_assignment":
                                await self.handle_get_assignment(chat_id, message_id, user_id)
                            elif data.startswith("answer_"):
                                # Передаем callback_query_id в метод handle_quiz_answer
                                await self.handle_quiz_answer(chat_id, message_id, user_id, data, query["id"])
                            elif data == "show_progress":
                                await self.show_progress(chat_id, message_id, user_id)
                            elif data == "show_study_plan":
                                await self.show_study_plan(chat_id, message_id, user_id)
                            elif data == "next_topic":
                                await self.handle_next_topic(chat_id, message_id, user_id)
                            elif data == "prev_topic":
                                await self.handle_prev_topic(chat_id, message_id, user_id)
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