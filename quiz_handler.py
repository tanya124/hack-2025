from typing import Dict, Any
import asyncio
from config import logger

class QuizSession:
    """Represents an active quiz session for a user"""
    
    def __init__(self, user_id: int, lesson_data: Dict[str, Any]):
        self.user_id = user_id
        self.lesson = lesson_data.get("lesson", "")
        self.question = lesson_data.get("question", "")
        self.options = lesson_data.get("options", [])
        self.correct_answer = lesson_data.get("correct_answer", "")
        self.answered = False
        self.user_answer = None
    
    def is_correct(self, answer: str) -> bool:
        """Check if the provided answer is correct"""
        return answer == self.correct_answer
    
    def set_user_answer(self, answer: str):
        """Set the user's answer and mark as answered"""
        self.user_answer = answer
        self.answered = True

class QuizHandler:
    """Manages quiz sessions for multiple users"""
    
    def __init__(self):
        self.active_sessions: Dict[int, QuizSession] = {}
    
    def create_session(self, user_id: int, lesson_data: Dict[str, Any]) -> QuizSession:
        """Create a new quiz session for a user"""
        session = QuizSession(user_id, lesson_data)
        self.active_sessions[user_id] = session
        logger.info(f"Created quiz session for user {user_id}")
        return session
    
    def get_session(self, user_id: int) -> QuizSession:
        """Get the active quiz session for a user"""
        return self.active_sessions.get(user_id)
    
    def end_session(self, user_id: int):
        """End the quiz session for a user"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            logger.info(f"Ended quiz session for user {user_id}")
    
    def has_active_session(self, user_id: int) -> bool:
        """Check if user has an active quiz session"""
        return user_id in self.active_sessions and not self.active_sessions[user_id].answered
    
    def format_lesson_message(self, session: QuizSession) -> str:
        """Format the lesson and question message"""
        message = f"📚 **Урок по старославянскому языку**\n\n"
        message += f"{session.lesson}\n\n"
        message += f"❓ **Вопрос:**\n{session.question}"
        return message
    
    def format_result_message(self, session: QuizSession, is_correct: bool, feedback: str = None) -> str:
        """Format the quiz result message"""
        if is_correct:
            result = "✅ **Правильно!**"
        else:
            result = f"❌ **Неправильно.**\n🎯 Правильный ответ: **{session.correct_answer}**"
        
        message = f"{result}\n\n"
        if feedback:
            message += f"💡 {feedback}\n\n"
        
        message += "Нажмите «Получить задание» для нового урока!"
        return message

# Create global instance
quiz_handler = QuizHandler()
