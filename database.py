import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config import logger
from datetime import datetime

class Database:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('PGHOST'),
            'database': os.getenv('PGDATABASE'),
            'user': os.getenv('PGUSER'),
            'password': os.getenv('PGPASSWORD'),
            'port': os.getenv('PGPORT')
        }
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Progress table
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
                
                self.connection.commit()
                logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
    
    def save_user(self, user_id, username=None, first_name=None, level=None, goal=None):
        """Save or update user information"""
        try:
            self.ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, level, goal)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = COALESCE(EXCLUDED.username, users.username),
                        first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                        level = COALESCE(EXCLUDED.level, users.level),
                        goal = COALESCE(EXCLUDED.goal, users.goal),
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, username, first_name, level, goal))
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

# Global database instance
db = Database()