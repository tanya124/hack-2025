import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
try:
    from telegram.constants import ParseMode
except ImportError:
    # Fallback for older versions
    from telegram import ParseMode

from config import TELEGRAM_BOT_TOKEN, logger
from openai_service import openai_service
from quiz_handler import quiz_handler

class OldChurchSlavonicBot:
    """Main bot class for Inter-Slavic learning"""
    
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up all bot command and callback handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started the bot")
        
        welcome_message = (
            f"Добро пожаловать, {user.first_name}! 👋\n\n"
            "🏛️ **Бот для изучения межславянского языка**\n\n"
            "Здесь вы изучите основы межславянского языка через короткие уроки "
            "и интерактивные задания. Каждый урок содержит теоретическое объяснение "
            "и вопрос для закрепления материала.\n\n"
            "Нажмите кнопку ниже, чтобы получить первое задание!"
        )
        
        keyboard = [[InlineKeyboardButton("📖 Получить задание", callback_data="get_assignment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🤖 **Помощь по боту**\n\n"
            "**Доступные команды:**\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n\n"
            "**Как пользоваться:**\n"
            "1. Нажмите «Получить задание» для нового урока\n"
            "2. Прочитайте теоретическое объяснение\n"
            "3. Ответьте на вопрос, выбрав один из вариантов\n"
            "4. Получите обратную связь и переходите к следующему уроку\n\n"
            "Удачи в изучении межславянского языка! 📚"
        )
        
        keyboard = [[InlineKeyboardButton("📖 Получить задание", callback_data="get_assignment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        try:
            if data == "get_assignment":
                await self.handle_get_assignment(query, user_id)
            elif data.startswith("answer_"):
                await self.handle_quiz_answer(query, user_id, data)
            else:
                logger.warning(f"Unknown callback data: {data}")
        
        except Exception as e:
            logger.error(f"Error handling callback {data} for user {user_id}: {e}")
            await query.edit_message_text(
                "😔 Произошла ошибка. Попробуйте снова.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📖 Получить задание", callback_data="get_assignment")
                ]])
            )
    
    async def handle_get_assignment(self, query, user_id: int):
        """Handle request for new assignment"""
        # End any existing session
        quiz_handler.end_session(user_id)
        
        # Show loading message
        await query.edit_message_text("⏳ Генерируем новое задание...")
        
        try:
            # Generate lesson and quiz using OpenAI
            lesson_data = await openai_service.generate_lesson_and_quiz()
            
            # Create new quiz session
            session = quiz_handler.create_session(user_id, lesson_data)
            
            # Format and send lesson message with quiz options
            message = quiz_handler.format_lesson_message(session)
            
            # Create keyboard with answer options
            keyboard = []
            for i, option in enumerate(session.options):
                keyboard.append([InlineKeyboardButton(
                    option,
                    callback_data=f"answer_{i}_{option}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error generating assignment for user {user_id}: {e}")
            await query.edit_message_text(
                f"😔 Ошибка при создании задания: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📖 Попробовать снова", callback_data="get_assignment")
                ]])
            )
    
    async def handle_quiz_answer(self, query, user_id: int, callback_data: str):
        """Handle quiz answer submission"""
        session = quiz_handler.get_session(user_id)
        
        if not session:
            await query.edit_message_text(
                "❌ Сессия истекла. Получите новое задание.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📖 Получить задание", callback_data="get_assignment")
                ]])
            )
            return
        
        if session.answered:
            await query.answer("Вы уже ответили на этот вопрос!")
            return
        
        # Parse the answer from callback data
        try:
            parts = callback_data.split("_", 2)
            option_index = int(parts[1])
            user_answer = parts[2]
        except (IndexError, ValueError):
            logger.error(f"Invalid callback data format: {callback_data}")
            await query.answer("Ошибка в формате ответа")
            return
        
        # Set user answer
        session.set_user_answer(user_answer)
        is_correct = session.is_correct(user_answer)
        
        # Show loading message for feedback generation
        await query.edit_message_text("⏳ Проверяем ответ...")
        
        try:
            # Generate personalized feedback
            feedback = await openai_service.generate_feedback(
                session.question, user_answer, session.correct_answer, is_correct
            )
        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            feedback = None
        
        # Format and send result
        result_message = quiz_handler.format_result_message(session, is_correct, feedback)
        
        keyboard = [[InlineKeyboardButton("📖 Получить задание", callback_data="get_assignment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            result_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # End the quiz session
        quiz_handler.end_session(user_id)
        
        # Log result
        logger.info(f"User {user_id} answered {'correctly' if is_correct else 'incorrectly'}")
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Inter-Slavic Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run the bot"""
    bot = OldChurchSlavonicBot()
    bot.run()

if __name__ == "__main__":
    main()
