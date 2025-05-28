import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config import logger
from datetime import datetime
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

class Database:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('PGHOST'),
            'database': os.getenv('PGDATABASE'),
            'user': os.getenv('PGUSER'),
            'password': os.getenv('PGPASSWORD'),
            'port': int(os.getenv('PGPORT', '5432'))
        }
        logger.info(f"Database connection params: host={os.getenv('PGHOST')}, db={os.getenv('PGDATABASE')}, user={os.getenv('PGUSER')}, port={os.getenv('PGPORT')}")

        self.connection = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            if self.connection:
                self.connection.close()
            self.connection = psycopg2.connect(**self.connection_params)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def ensure_connection(self):
        """Ensure database connection is alive"""
        try:
            if not self.connection or self.connection.closed:
                self.connect()
            else:
                # Test connection
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
        except Exception as e:
            logger.warning(f"Connection lost, reconnecting: {e}")
            self.connect()
    
    def create_tables(self):
        """Create necessary tables"""
        try:
            with self.connection.cursor() as cursor:
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        level VARCHAR(50),
                        goal VARCHAR(100),
                        avatar VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
""")
                
                # Проверяем и добавляем колонку current_topic_id, если она не существует
                try:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'current_topic_id'
                    """)
                    if not cursor.fetchone():
                        cursor.execute("""
                            ALTER TABLE users 
                            ADD COLUMN current_topic_id INTEGER
                        """)
                        self.connection.commit()
                        logger.info("Added current_topic_id column to users table")
                        
                    # Проверяем и добавляем колонку avatar, если она не существует
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'avatar'
                    """)
                    if not cursor.fetchone():
                        cursor.execute("""
                            ALTER TABLE users 
                            ADD COLUMN avatar VARCHAR(50)
                        """)
                        self.connection.commit()
                        logger.info("Added avatar column to users table")
                except Exception as e:
                    logger.error(f"Error checking or adding columns to users table: {e}")
                
                # Old Progress table (keeping for backward compatibility)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS progress (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        lesson_topic VARCHAR(255),
                        question TEXT,
                        user_answer VARCHAR(255),
                        correct_answer VARCHAR(255),
                        is_correct BOOLEAN,
                        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Study Plans table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS study_plans (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        level VARCHAR(50),
                        goal VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Study Plan Items table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS study_plan_items (
                        id SERIAL PRIMARY KEY,
                        study_plan_id INTEGER REFERENCES study_plans(id),
                        topic VARCHAR(255),
                        description TEXT,
                        order_number INTEGER,
                        bloom_level INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # New Progress table for tracking progress on study plan items
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS study_progress (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        study_plan_item_id INTEGER REFERENCES study_plan_items(id),
                        is_completed BOOLEAN DEFAULT FALSE,
                        current_bloom_level INTEGER DEFAULT 1,
                        correct_answers INTEGER DEFAULT 0,
                        total_attempts INTEGER DEFAULT 0,
                        last_attempt_at TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """)
                
                # Words table for the "Ritual of the Word" feature
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS words (
                        id SERIAL PRIMARY KEY,
                        word VARCHAR(255) NOT NULL,
                        meaning_ru TEXT,
                        part_of_speech VARCHAR(50),
                        level VARCHAR(50),
                        tag VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if words table is empty and populate it with some initial words
                cursor.execute("SELECT COUNT(*) FROM words")
                word_count = cursor.fetchone()[0]
                
                if word_count == 0:
                    # Populate with some initial words
                    initial_words = [
                        ("svoboda", "свобода, воля", "n.", "beginner", "basic"),
                        ("ljubiti", "любить", "v.", "beginner", "basic"),
                        ("slovo", "слово", "n.", "beginner", "basic"),
                        ("čelovek", "человек", "n.", "beginner", "basic"),
                        ("zemja", "земля", "n.", "beginner", "basic"),
                        ("voda", "вода", "n.", "beginner", "basic"),
                        ("ogonj", "огонь", "n.", "beginner", "basic"),
                        ("dom", "дом", "n.", "beginner", "basic"),
                        ("duša", "душа", "n.", "beginner", "basic"),
                        ("serce", "сердце", "n.", "beginner", "basic"),
                        ("mir", "мир, покой", "n.", "beginner", "basic"),
                        ("život", "жизнь", "n.", "beginner", "basic"),
                        ("mudrost", "мудрость", "n.", "beginner", "basic"),
                        ("istina", "истина, правда", "n.", "beginner", "basic"),
                        ("sila", "сила", "n.", "beginner", "basic"),
                        ("radost", "радость", "n.", "beginner", "basic"),
                        ("svetlo", "свет", "n.", "beginner", "basic"),
                        ("tma", "тьма", "n.", "beginner", "basic"),
                        ("dobro", "добро", "n.", "beginner", "basic"),
                        ("zlo", "зло", "n.", "beginner", "basic"),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO words (word, meaning_ru, part_of_speech, level, tag)
                        VALUES (%s, %s, %s, %s, %s)
                    """, initial_words)
                    
                    logger.info(f"Populated words table with {len(initial_words)} initial words")
                    self.connection.commit()
                
                self.connection.commit()
                logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
    
    def save_user(self, user_id, username=None, first_name=None, level=None, goal=None, avatar=None):
        """Save or update user information"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, level, goal, avatar)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = COALESCE(EXCLUDED.username, users.username),
                        first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                        level = COALESCE(EXCLUDED.level, users.level),
                        goal = COALESCE(EXCLUDED.goal, users.goal),
                        avatar = COALESCE(EXCLUDED.avatar, users.avatar),
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, username, first_name, level, goal, avatar))
                self.connection.commit()
                logger.info(f"User {user_id} saved successfully")
        except Exception as e:
            logger.error(f"Failed to save user: {e}")
            self.connection.rollback()
    
    def get_user(self, user_id):
        """Get user information"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    def save_progress(self, user_id, lesson_topic, question, user_answer, correct_answer, is_correct):
        """Save user progress"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO progress (user_id, lesson_topic, question, user_answer, correct_answer, is_correct)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, lesson_topic, question, user_answer, correct_answer, is_correct))
                self.connection.commit()
                logger.info(f"Progress saved for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
            self.connection.rollback()
    
    def get_user_progress(self, user_id):
        """Get user progress history"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM progress 
                    WHERE user_id = %s 
                    ORDER BY completed_at DESC
                    LIMIT 10
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
            return []
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_lessons,
                        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                        COUNT(DISTINCT DATE(completed_at)) as days_active
                    FROM progress 
                    WHERE user_id = %s
                """, (user_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'total_lessons': 0, 'correct_answers': 0, 'days_active': 0}

    def save_study_plan(self, user_id, level, goal, study_plan_items):
        """Save a user's study plan"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                # Check if user already has a study plan
                cursor.execute("""
                    SELECT id FROM study_plans WHERE user_id = %s
                """, (user_id,))
                existing_plan = cursor.fetchone()
                
                if existing_plan:
                    # Delete existing study plan and its items
                    plan_id = existing_plan[0]
                    cursor.execute("DELETE FROM study_progress WHERE study_plan_item_id IN (SELECT id FROM study_plan_items WHERE study_plan_id = %s)", (plan_id,))
                    cursor.execute("DELETE FROM study_plan_items WHERE study_plan_id = %s", (plan_id,))
                    cursor.execute("DELETE FROM study_plans WHERE id = %s", (plan_id,))
                
                # Create new study plan record
                cursor.execute("""
                    INSERT INTO study_plans (user_id, level, goal)
                    VALUES (%s, %s, %s) RETURNING id
                """, (user_id, level, goal))
                study_plan_id = cursor.fetchone()[0]
                
                # Insert study plan items
                for i, item in enumerate(study_plan_items):
                    cursor.execute("""
                        INSERT INTO study_plan_items 
                        (study_plan_id, topic, description, order_number, bloom_level)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (study_plan_id, item['topic'], item['description'], i+1, 1))
                    item_id = cursor.fetchone()[0]
                    
                    # Initialize progress for this item
                    cursor.execute("""
                        INSERT INTO study_progress
                        (user_id, study_plan_item_id, is_completed, current_bloom_level)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, item_id, False, 1))
                
                # Set the first topic as current
                cursor.execute("""
                    SELECT id FROM study_plan_items 
                    WHERE study_plan_id = %s 
                    ORDER BY order_number ASC LIMIT 1
                """, (study_plan_id,))
                first_item = cursor.fetchone()
                if first_item:
                    try:
                        # Проверяем наличие колонки current_topic_id
                        cursor.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'users' AND column_name = 'current_topic_id'
                        """)
                        if cursor.fetchone():
                            cursor.execute("""
                                UPDATE users SET current_topic_id = %s WHERE user_id = %s
                            """, (first_item[0], user_id))
                        else:
                            logger.warning(f"Column current_topic_id does not exist in users table. Skipping update.")
                    except Exception as e:
                        logger.warning(f"Failed to update current_topic_id: {e}. Continuing without setting current topic.")
                        # Продолжаем выполнение, даже если не удалось обновить current_topic_id
                
                self.connection.commit()
                logger.info(f"Study plan created for user {user_id}")
                return study_plan_id
        except Exception as e:
            logger.error(f"Failed to save study plan: {e}")
            self.connection.rollback()
            return None
    
    def get_user_study_plan(self, user_id):
        """Get a user's study plan with progress information"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get study plan
                cursor.execute("""
                    SELECT sp.id, sp.level, sp.goal
                    FROM study_plans sp
                    WHERE sp.user_id = %s
                    ORDER BY sp.created_at DESC
                    LIMIT 1
                """, (user_id,))
                study_plan = cursor.fetchone()
                
                if not study_plan:
                    return None
                
                # Get study plan items with progress
                cursor.execute("""
                    SELECT 
                        spi.id, spi.topic, spi.description, spi.order_number,
                        COALESCE(spr.current_bloom_level, 1) as current_bloom_level,
                        COALESCE(spr.is_completed, FALSE) as is_completed
                    FROM study_plan_items spi
                    LEFT JOIN study_progress spr ON spi.id = spr.study_plan_item_id AND spr.user_id = %s
                    WHERE spi.study_plan_id = %s
                    ORDER BY spi.order_number ASC
                """, (user_id, study_plan['id']))
                items = cursor.fetchall()
                
                # Convert to dictionary
                result = dict(study_plan)
                result['items'] = list(items)
                return result
        except Exception as e:
            logger.error(f"Failed to get user study plan: {e}")
            return None
    
    def get_current_topic(self, user_id):
        """Get the current topic for a user"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Проверяем наличие колонки current_topic_id
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'current_topic_id'
                """)
                if not cursor.fetchone():
                    # Если колонки нет, получаем первую тему из последнего учебного плана
                    cursor.execute("""
                        SELECT spi.id, spi.topic, spi.description, spi.order_number,
                               COALESCE(spr.current_bloom_level, 1) as current_bloom_level,
                               COALESCE(spr.is_completed, FALSE) as is_completed
                        FROM study_plans sp
                        JOIN study_plan_items spi ON sp.id = spi.study_plan_id
                        LEFT JOIN study_progress spr ON spi.id = spr.study_plan_item_id AND spr.user_id = %s
                        WHERE sp.user_id = %s
                        ORDER BY sp.created_at DESC, spi.order_number ASC
                        LIMIT 1
                    """, (user_id, user_id))
                    return cursor.fetchone()
                else:
                    # Если колонка есть, используем стандартный запрос
                    try:
                        cursor.execute("""
                            SELECT spi.id, spi.topic, spi.description, spi.order_number,
                                   COALESCE(spr.current_bloom_level, 1) as current_bloom_level,
                                   COALESCE(spr.is_completed, FALSE) as is_completed
                            FROM users u
                            JOIN study_plan_items spi ON u.current_topic_id = spi.id
                            LEFT JOIN study_progress spr ON spi.id = spr.study_plan_item_id AND spr.user_id = u.user_id
                            WHERE u.user_id = %s
                        """, (user_id,))
                        topic = cursor.fetchone()
                        if topic:
                            return topic
                        else:
                            # Если не нашли тему, возвращаемся к варианту с первой темой
                            cursor.execute("""
                                SELECT spi.id, spi.topic, spi.description, spi.order_number,
                                       COALESCE(spr.current_bloom_level, 1) as current_bloom_level,
                                       COALESCE(spr.is_completed, FALSE) as is_completed
                                FROM study_plans sp
                                JOIN study_plan_items spi ON sp.id = spi.study_plan_id
                                LEFT JOIN study_progress spr ON spi.id = spr.study_plan_item_id AND spr.user_id = %s
                                WHERE sp.user_id = %s
                                ORDER BY sp.created_at DESC, spi.order_number ASC
                                LIMIT 1
                            """, (user_id, user_id))
                            return cursor.fetchone()
                    except Exception as e:
                        logger.error(f"Failed to get current topic with current_topic_id: {e}")
                        # Если произошла ошибка, пробуем получить первую тему
                        cursor.execute("""
                            SELECT spi.id, spi.topic, spi.description, spi.order_number,
                                   COALESCE(spr.current_bloom_level, 1) as current_bloom_level,
                                   COALESCE(spr.is_completed, FALSE) as is_completed
                            FROM study_plans sp
                            JOIN study_plan_items spi ON sp.id = spi.study_plan_id
                            LEFT JOIN study_progress spr ON spi.id = spr.study_plan_item_id AND spr.user_id = %s
                            WHERE sp.user_id = %s
                            ORDER BY sp.created_at DESC, spi.order_number ASC
                            LIMIT 1
                        """, (user_id, user_id))
                        return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get current topic: {e}")
            return None
    
    def get_next_topic(self, user_id, current_topic_id):
        """Get the next topic in the study plan"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get current topic order
                cursor.execute("""
                    SELECT spi.study_plan_id, spi.order_number
                    FROM study_plan_items spi
                    WHERE spi.id = %s
                """, (current_topic_id,))
                current = cursor.fetchone()
                
                if not current:
                    return None
                
                # Get next topic
                cursor.execute("""
                    SELECT spi.id, spi.topic, spi.description, spi.order_number
                    FROM study_plan_items spi
                    WHERE spi.study_plan_id = %s AND spi.order_number > %s
                    ORDER BY spi.order_number ASC
                    LIMIT 1
                """, (current['study_plan_id'], current['order_number']))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get next topic: {e}")
            return None
    
    def get_prev_topic(self, user_id, current_topic_id):
        """Get the previous topic in the study plan"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get current topic order
                cursor.execute("""
                    SELECT spi.study_plan_id, spi.order_number
                    FROM study_plan_items spi
                    WHERE spi.id = %s
                """, (current_topic_id,))
                current = cursor.fetchone()
                
                if not current:
                    return None
                
                # Get previous topic
                cursor.execute("""
                    SELECT spi.id, spi.topic, spi.description, spi.order_number
                    FROM study_plan_items spi
                    WHERE spi.study_plan_id = %s AND spi.order_number < %s
                    ORDER BY spi.order_number DESC
                    LIMIT 1
                """, (current['study_plan_id'], current['order_number']))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get previous topic: {e}")
            return None
    
    def set_current_topic(self, user_id, topic_id):
        """Set the current topic for a user"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                # Проверяем наличие колонки current_topic_id
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'current_topic_id'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE users SET current_topic_id = %s WHERE user_id = %s
                    """, (topic_id, user_id))
                    self.connection.commit()
                    logger.info(f"Current topic set for user {user_id}")
                    return True
                else:
                    # Если колонки нет, пытаемся добавить ее
                    try:
                        cursor.execute("""
                            ALTER TABLE users 
                            ADD COLUMN current_topic_id INTEGER
                        """)
                        cursor.execute("""
                            UPDATE users SET current_topic_id = %s WHERE user_id = %s
                        """, (topic_id, user_id))
                        self.connection.commit()
                        logger.info(f"Added current_topic_id column and set current topic for user {user_id}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to add current_topic_id column: {e}")
                        self.connection.rollback()
                        return False
        except Exception as e:
            logger.error(f"Failed to set current topic: {e}")
            self.connection.rollback()
            return False
    
    def update_topic_progress(self, user_id, topic_id, new_bloom_level, is_completed, is_correct=False):
        """Update progress for a specific topic"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                # Check if progress entry exists
                cursor.execute("""
                    SELECT id, current_bloom_level, correct_answers_count 
                    FROM study_progress
                    WHERE user_id = %s AND study_plan_item_id = %s
                """, (user_id, topic_id))
                progress = cursor.fetchone()
                
                if progress:
                    # Update existing progress
                    if is_correct:
                        # Увеличиваем счетчик правильных ответов
                        new_count = progress[2] + 1 if progress[2] is not None else 1
                        
                        if is_completed:
                            cursor.execute("""
                                UPDATE study_progress
                                SET current_bloom_level = %s, is_completed = %s, 
                                    completed_at = CURRENT_TIMESTAMP, correct_answers_count = %s
                                WHERE user_id = %s AND study_plan_item_id = %s
                            """, (new_bloom_level, is_completed, new_count, user_id, topic_id))
                        else:
                            cursor.execute("""
                                UPDATE study_progress
                                SET current_bloom_level = %s, is_completed = %s, 
                                    last_attempt_at = CURRENT_TIMESTAMP, correct_answers_count = %s
                                WHERE user_id = %s AND study_plan_item_id = %s
                            """, (new_bloom_level, is_completed, new_count, user_id, topic_id))
                    else:
                        # Неверный ответ, сбрасываем счетчик правильных ответов
                        if is_completed:
                            cursor.execute("""
                                UPDATE study_progress
                                SET current_bloom_level = %s, is_completed = %s, 
                                    completed_at = CURRENT_TIMESTAMP, correct_answers_count = 0
                                WHERE user_id = %s AND study_plan_item_id = %s
                            """, (new_bloom_level, is_completed, user_id, topic_id))
                        else:
                            cursor.execute("""
                                UPDATE study_progress
                                SET current_bloom_level = %s, is_completed = %s, 
                                    last_attempt_at = CURRENT_TIMESTAMP, correct_answers_count = 0
                                WHERE user_id = %s AND study_plan_item_id = %s
                            """, (new_bloom_level, is_completed, user_id, topic_id))
                else:
                    # Create new progress entry
                    cursor.execute("""
                        INSERT INTO study_progress
                        (user_id, study_plan_item_id, current_bloom_level, is_completed, correct_answers_count)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, topic_id, new_bloom_level, is_completed, 1 if is_correct else 0))
                
                self.connection.commit()
                logger.info(f"Topic progress updated for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update topic progress: {e}")
            self.connection.rollback()
            return False
    
    def get_topic_name(self, topic_id):
        """Get topic name by id"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT topic FROM study_plan_items WHERE id = %s
                """, (topic_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            logger.error(f"Failed to get topic name: {e}")
            return ""
            
    def get_random_words(self, count=100):
        """Get random words from the dictionary
        
        Parameters:
        count (int): Number of words to return
        
        Returns:
        list: List of dictionaries with word information
        """
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Получаем случайные слова из словаря
                query = "SELECT * FROM words ORDER BY RANDOM() LIMIT %s"
                cursor.execute(query, [count])
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get random words: {e}")
            return []
            
    def get_random_word_for_ritual(self):
        """Get a single random word for the 'Ritual of the Word' feature
        
        Returns:
        dict: Dictionary with word information or None if no words found
        """
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get a random word from the dictionary
                query = "SELECT * FROM words ORDER BY RANDOM() LIMIT 1"
                cursor.execute(query)
                word = cursor.fetchone()
                
                # If no word found, return a default word
                if not word:
                    return {
                        "word": "svoboda",
                        "meaning_ru": "свобода, воля"
                    }
                    
                return word
        except Exception as e:
            logger.error(f"Failed to get random word for ritual: {e}")
            # Return a default word if there's an error
            return {
                "word": "svoboda",
                "meaning_ru": "свобода, воля"
            }
            
    def get_all_active_users(self):
        """Get all active users who have allowed messages
        
        Returns:
        list: List of dictionaries with user information
        """
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Check if the allow_messages column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'allow_messages'
                """)
                
                if not cursor.fetchone():
                    # Add the allow_messages column if it doesn't exist
                    cursor.execute("""
                        ALTER TABLE users 
                        ADD COLUMN allow_messages BOOLEAN DEFAULT TRUE
                    """)
                    self.connection.commit()
                    logger.info("Added allow_messages column to users table")
                
                # Get all users who have allowed messages
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE allow_messages = TRUE
                """)
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return []

    def update_progress(self, user_id, study_plan_item_id, is_correct):
        """Update a user's progress on a study plan item"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                # Get current progress
                cursor.execute("""
                    SELECT current_bloom_level, correct_answers, total_attempts, is_completed
                    FROM study_progress
                    WHERE user_id = %s AND study_plan_item_id = %s
                """, (user_id, study_plan_item_id))
                
                result = cursor.fetchone()
                if not result:
                    return False
                    
                current_bloom_level, correct_answers, total_attempts, is_completed = result
                
                # Update counters
                total_attempts += 1
                if is_correct:
                    correct_answers += 1
                
                # Check conditions for advancing to next level or completing the topic
                # Condition: 3 correct answers to advance to next level
                completion_threshold = 3
                
                if is_correct and correct_answers % completion_threshold == 0:
                    if current_bloom_level < 6:  # Max Bloom's taxonomy level
                        current_bloom_level += 1
                    else:
                        is_completed = True
                        
                # Update progress
                cursor.execute("""
                    UPDATE study_progress
                    SET current_bloom_level = %s,
                        correct_answers = %s,
                        total_attempts = %s,
                        is_completed = %s,
                        last_attempt_at = CURRENT_TIMESTAMP,
                        completed_at = CASE WHEN %s AND NOT is_completed THEN CURRENT_TIMESTAMP ELSE completed_at END
                    WHERE user_id = %s AND study_plan_item_id = %s
                """, (
                    current_bloom_level, 
                    correct_answers, 
                    total_attempts, 
                    is_completed,
                    is_completed,
                    user_id, 
                    study_plan_item_id
                ))
                
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
            self.connection.rollback()
            return False

    def get_current_topic(self, user_id):
        """Get the current topic for a user"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT spi.id, spi.topic, spi.description, spi.bloom_level,
                           p.current_bloom_level, p.is_completed
                    FROM users u
                    JOIN study_plan_items spi ON u.current_topic_id = spi.id
                    JOIN study_progress p ON spi.id = p.study_plan_item_id AND p.user_id = u.user_id
                    WHERE u.user_id = %s
                """, (user_id,))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get current topic: {e}")
            return None

    def get_topic_by_id(self, topic_id):
        """Get information about a topic by ID"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT spi.id, spi.topic, spi.description, spi.bloom_level,
                           p.current_bloom_level, p.is_completed, p.correct_answers, p.total_attempts
                    FROM study_plan_items spi
                    JOIN study_progress p ON spi.id = p.study_plan_item_id
                    WHERE spi.id = %s
                """, (topic_id,))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get topic by id: {e}")
            return None

    def get_next_topic(self, user_id, current_topic_id):
        """Get the next topic in a user's study plan"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get current topic order number and study plan ID
                cursor.execute("""
                    SELECT order_number, study_plan_id
                    FROM study_plan_items
                    WHERE id = %s
                """, (current_topic_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                    
                current_order = result["order_number"]
                study_plan_id = result["study_plan_id"]
                
                # Get next topic
                cursor.execute("""
                    SELECT spi.id, spi.topic, spi.description, spi.bloom_level,
                           p.current_bloom_level, p.is_completed
                    FROM study_plan_items spi
                    JOIN study_progress p ON spi.id = p.study_plan_item_id AND p.user_id = %s
                    WHERE spi.study_plan_id = %s AND spi.order_number > %s
                    ORDER BY spi.order_number
                    LIMIT 1
                """, (user_id, study_plan_id, current_order))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get next topic: {e}")
            return None

    def get_prev_topic(self, user_id, current_topic_id):
        """Get the previous topic in a user's study plan"""
        try:
            self.ensure_connection()
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get current topic order number and study plan ID
                cursor.execute("""
                    SELECT order_number, study_plan_id
                    FROM study_plan_items
                    WHERE id = %s
                """, (current_topic_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                    
                current_order = result["order_number"]
                study_plan_id = result["study_plan_id"]
                
                # Get previous topic
                cursor.execute("""
                    SELECT spi.id, spi.topic, spi.description, spi.bloom_level,
                           p.current_bloom_level, p.is_completed
                    FROM study_plan_items spi
                    JOIN study_progress p ON spi.id = p.study_plan_item_id AND p.user_id = %s
                    WHERE spi.study_plan_id = %s AND spi.order_number < %s
                    ORDER BY spi.order_number DESC
                    LIMIT 1
                """, (user_id, study_plan_id, current_order))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get previous topic: {e}")
            return None

    def set_current_topic(self, user_id, topic_id):
        """Set the current topic for a user"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET current_topic_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (topic_id, user_id))
                
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to set current topic: {e}")
            self.connection.rollback()
            return False

# Global database instance
db = Database()