import json
import openai
from openai import OpenAI
from config import OPENAI_API_KEY, LESSON_PROMPT, logger

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
client = OpenAI(api_key=OPENAI_API_KEY)

class OpenAIService:
    def __init__(self):
        self.client = client
    
    async def generate_lesson_and_quiz(self):
        """
        Generate a micro-lesson and quiz about Old Church Slavonic using OpenAI API
        Returns a dictionary with lesson, question, options, and correct_answer
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты опытный преподаватель старославянского языка. Создавай качественные образовательные материалы для начинающих."
                    },
                    {
                        "role": "user", 
                        "content": LESSON_PROMPT
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            lesson_data = json.loads(content)
            
            # Validate the response structure
            required_keys = ["lesson", "question", "options", "correct_answer"]
            for key in required_keys:
                if key not in lesson_data:
                    raise ValueError(f"Missing required key: {key}")
            
            # Validate options list
            if not isinstance(lesson_data["options"], list) or len(lesson_data["options"]) < 2:
                raise ValueError("Options must be a list with at least 2 items")
            
            # Validate correct_answer is in options
            if lesson_data["correct_answer"] not in lesson_data["options"]:
                raise ValueError("Correct answer must be one of the options")
            
            logger.info("Successfully generated lesson and quiz")
            return lesson_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise Exception("Ошибка при обработке ответа от AI. Попробуйте снова.")
        
        except openai.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            raise Exception("Превышен лимит запросов к AI. Попробуйте позже.")
        
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception("Ошибка API. Попробуйте снова через несколько минут.")
        
        except Exception as e:
            logger.error(f"Unexpected error in generate_lesson_and_quiz: {e}")
            raise Exception("Произошла неожиданная ошибка. Попробуйте снова.")
    
    async def generate_feedback(self, question, user_answer, correct_answer, is_correct):
        """
        Generate feedback for the user's answer using OpenAI
        """
        try:
            feedback_prompt = f"""
            Пользователь отвечал на вопрос по старославянскому языку:
            Вопрос: {question}
            Правильный ответ: {correct_answer}
            Ответ пользователя: {user_answer}
            Результат: {'правильно' if is_correct else 'неправильно'}
            
            Дай краткую обратную связь (1-2 предложения) на русском языке. 
            Если ответ правильный - похвали и добавь интересный факт.
            Если неправильный - объясни, почему правильный ответ верен.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты преподаватель старославянского языка. Давай конструктивную обратную связь студентам."
                    },
                    {
                        "role": "user",
                        "content": feedback_prompt
                    }
                ],
                temperature=0.6,
                max_tokens=200
            )
            
            feedback = response.choices[0].message.content.strip()
            logger.info("Successfully generated feedback")
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            # Return default feedback if AI fails
            if is_correct:
                return "✅ Правильно! Отличная работа!"
            else:
                return f"❌ Неправильно. Правильный ответ: {correct_answer}"

# Create global instance
openai_service = OpenAIService()
