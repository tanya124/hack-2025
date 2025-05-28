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
    
    async def generate_lesson_and_quiz(self, topic_name=None, bloom_level=1):
        """
        Generate a micro-lesson and quiz about Inter-Slavic using OpenAI API
        based on the specified topic and Bloom's taxonomy level.
        
        Parameters:
        - topic_name: The specific topic to create a lesson about (optional)
        - bloom_level: Bloom's taxonomy level (1-6)
                      1 = Remember, 2 = Understand, 3 = Apply,
                      4 = Analyze, 5 = Evaluate, 6 = Create
        
        Returns a dictionary with lesson, question, options, and correct_answer
        """
        try:
            # Define Bloom's taxonomy levels and corresponding task types
            bloom_taxonomy = {
                1: "запоминание (вспомнить факты, термины, основные понятия)",
                2: "понимание (объяснить идеи или концепции, интерпретировать информацию)",
                3: "применение (использовать информацию в новой ситуации)",
                4: "анализ (выявить связи между идеями, структурировать информацию)",
                5: "оценка (обосновать точку зрения, оценить решение)",
                6: "творчество (создать новый продукт или точку зрения)"
            }
            
            # Create prompt based on topic and Bloom's level
            if topic_name:
                prompt = f"""
                Создай короткий урок и тест по теме "{topic_name}" в изучении межславянского языка.
                
                Задание должно соответствовать уровню {bloom_level} по таксономии Блума: {bloom_taxonomy[bloom_level]}.
                
                Урок должен быть кратким (3-5 предложений), но информативным, с примерами.
                
                Вопрос должен проверять именно уровень {bloom_taxonomy[bloom_level]}.
                
                Создай 4 варианта ответа, один из которых правильный.
                
                Верни результат в формате JSON с полями:
                - lesson: текст урока
                - question: вопрос по материалу урока
                - options: массив из 4 вариантов ответа
                - correct_answer: правильный ответ (должен точно совпадать с одним из вариантов в options)
                """
            else:
                # Use default prompt if no topic specified
                prompt = LESSON_PROMPT
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты опытный преподаватель межславянского языка. Создавай качественные образовательные материалы, соответствующие указанному уровню по таксономии Блума."
                    },
                    {
                        "role": "user", 
                        "content": prompt
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
    
    async def generate_feedback(self, question, user_answer, correct_answer, is_correct, avatar=None):
        """
        Generate feedback for the user's answer using OpenAI
        """
        try:
            # Define avatar communication styles
            avatar_styles = {
                "vedunia": "Speak with warmth, wisdom, and encouragement. Use rich but understandable language. Be supportive and motherly.",
                "bolgar": "Speak with clarity, depth, and honor. Be friendly and respectful. Convey a sense of being a reliable ally.",
                "starec": "Speak in a calm, encouraging, and wise manner. Use meditative speech with notes of antiquity. Talk as if a grandfather to a grandson.",
                "polyak": "Speak in a modern, playful, and lively style. Use youth language, humor, simplicity, and vigor."
            }
            
            # Get the avatar style instruction
            avatar_style = ""
            if avatar and avatar in avatar_styles:
                avatar_style = f"\n\nCommunication style: {avatar_styles[avatar]}\n"
            
            feedback_prompt = f"""
            Пользователь отвечал на вопрос по межславянскому языку:
            Вопрос: {question}
            Правильный ответ: {correct_answer}
            Ответ пользователя: {user_answer}
            Результат: {'правильно' if is_correct else 'неправильно'}{avatar_style}
            
            Дай краткую обратную связь (1-2 предложения) на русском языке. 
            Если ответ правильный - похвали и добавь интересный факт.
            Если неправильный - объясни, почему правильный ответ верен.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты преподаватель межславянского языка. Давай конструктивную обратную связь студентам."
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

    async def generate_study_plan(self, level, goal, avatar=None):
        """
        Generate a study plan for learning Inter-Slavic based on user level and goal
        Returns a list of study plan items with topics, descriptions, and Bloom's taxonomy levels
        """
        try:
            # Define avatar communication styles
            avatar_styles = {
                "vedunia": "Speak with warmth, wisdom, and encouragement. Use rich but understandable language. Be supportive and motherly.",
                "bolgar": "Speak with clarity, depth, and honor. Be friendly and respectful. Convey a sense of being a reliable ally.",
                "starec": "Speak in a calm, encouraging, and wise manner. Use meditative speech with notes of antiquity. Talk as if a grandfather to a grandson.",
                "polyak": "Speak in a modern, playful, and lively style. Use youth language, humor, simplicity, and vigor."
            }
            
            # Get the avatar style instruction
            avatar_style = ""
            if avatar and avatar in avatar_styles:
                avatar_style = f"\n\nCommunication style: {avatar_styles[avatar]}\n"
            
            prompt = f"""
            Create a study plan for learning Inter-Slavic (межславянский язык) for a user with level "{level}" 
            and learning goal "{goal}". The plan should be based on the textbook "Interslavic zonal contructed language: An introduction" 
            and contain sequential topics for study.{avatar_style}
            
            For each topic, provide:
            1. Topic name (short, 3-5 words)
            2. Brief description (1-2 sentences)
            3. Bloom's taxonomy level (from 1 to 6)
            
            The study plan should include at least 10 topics, covering:
            - Alphabet and pronunciation
            - Basic vocabulary
            - Grammar fundamentals
            - Sentence structure
            - Reading and comprehension
            - Cultural context
            
            Return the result as a JSON array:
            [
              {{
                "topic": "Topic name",
                "description": "Brief description",
                "bloom_level": 1
              }},
              ...
            ]
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert in Inter-Slavic language and pedagogical design. Create a structured study plan."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            study_plan_data = json.loads(content)
            
            # Ensure we have a list of study plan items
            if isinstance(study_plan_data, dict) and "study_plan" in study_plan_data:
                study_plan_items = study_plan_data["study_plan"]
            elif isinstance(study_plan_data, list):
                study_plan_items = study_plan_data
            else:
                raise ValueError("Invalid study plan format")
            
            # Validate each item
            for item in study_plan_items:
                if not all(key in item for key in ["topic", "description", "bloom_level"]):
                    raise ValueError(f"Missing required keys in study plan item: {item}")
            
            logger.info(f"Generated study plan with {len(study_plan_items)} topics")
            return study_plan_items
            
        except Exception as e:
            logger.error(f"Failed to generate study plan: {e}")
            raise Exception("Error generating study plan. Please try again.")
    
    async def generate_lesson_and_quiz(self, topic=None, bloom_level=None, dictionary_words=None, avatar=None):
        """
        Generate a micro-lesson and quiz about Inter-Slavic using OpenAI API
        Returns a dictionary with lesson, question, options, and correct_answer
        
        Parameters:
        topic (str, optional): Topic for the lesson
        bloom_level (int, optional): Bloom's taxonomy level (1-6)
        dictionary_words (list, optional): List of dictionary words to use in the lesson
        
        If topic and bloom_level are provided, generates content specific to that topic and level
        Otherwise, generates a random lesson
        """
        try:
            # Define task types based on Bloom's taxonomy level
            task_types = {
                1: "Слово дня",
                2: "Найди смысл",
                3: "Собери фразу",
                4: "Что здесь не так?",
                5: "Сравни переводы",
                6: "Сочини своё"
            }
            
            # Подготовка словарных слов для использования в промпте
            dictionary_content = ""
            if dictionary_words and len(dictionary_words) > 0:
                dictionary_content = "Use ONLY these Inter-Slavic words in your lesson and quiz:\n\n"
                for word in dictionary_words:
                    # Добавляем основную информацию о слове
                    dictionary_content += f"- {word['isv']} "
                    if word.get('addition'):
                        dictionary_content += f"({word['addition']}) "
                    dictionary_content += f"[{word.get('partOfSpeech', '')}]: "
                    
                    # Добавляем переводы на русский и английский
                    translations = []
                    if word.get('ru'):
                        translations.append(f"RU: {word['ru']}")
                    if word.get('en'):
                        translations.append(f"EN: {word['en']}")
                    
                    dictionary_content += ", ".join(translations) + "\n"
            
            # Define avatar communication styles
            avatar_styles = {
                "vedunia": "Speak with warmth, wisdom, and encouragement. Use rich but understandable language. Be supportive and motherly.",
                "bolgar": "Speak with clarity, depth, and honor. Be friendly and respectful. Convey a sense of being a reliable ally.",
                "starec": "Speak in a calm, encouraging, and wise manner. Use meditative speech with notes of antiquity. Talk as if a grandfather to a grandson.",
                "polyak": "Speak in a modern, playful, and lively style. Use youth language, humor, simplicity, and vigor."
            }
            
            # Get the avatar style instruction
            avatar_style = ""
            if avatar and avatar in avatar_styles:
                avatar_style = f"\n\nCommunication style: {avatar_styles[avatar]}\n"
            
            if topic and bloom_level:
                # Generate content specific to the topic and Bloom's level
                task_type = task_types.get(bloom_level, "Слово дня")
                
                prompt = f"""
                Create a micro-lesson about Inter-Slavic (межславянский язык) on the topic "{topic}" 
                with difficulty level {bloom_level} (Bloom's taxonomy).{avatar_style}
                
                Task type: "{task_type}"
                
                The lesson should include:
                1. Brief theoretical explanation (3-5 sentences) in Russian
                2. One question in the format corresponding to the task type
                3. Answer options (2-4 options)
                4. Correct answer
                
                Use materials from the textbook "Interslavic zonal contructed language: An introduction".
                
                {dictionary_content}
                
                Return the result in JSON format:
                {{
                  "lesson": "Theoretical explanation",
                  "task_type": "{task_type}",
                  "question": "Question",
                  "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                  "correct_answer": "Correct answer"
                }}
                """
                
                system_prompt = "You are an experienced Inter-Slavic language teacher. Create quality educational materials based on the textbook. Use ONLY the provided Inter-Slavic words to avoid hallucinations."
            else:
                # Use the default prompt for random lessons
                prompt = LESSON_PROMPT
                system_prompt = "Ты опытный преподаватель межславянского языка. Создавай качественные образовательные материалы для начинающих."
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": prompt
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

# Create global instance
openai_service = OpenAIService()
