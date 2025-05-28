#!/usr/bin/env python3

import asyncio
import logging
import json
import httpx
from datetime import datetime
from database import db
from openai_service import openai_service
from config import TELEGRAM_BOT_TOKEN, logger

class DailyRitualSender:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = httpx.AsyncClient(timeout=60.0)
    
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
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return {"ok": False}
    
    async def generate_ritual_message(self, user_id):
        """Generate a ritual message for a user"""
        try:
            # Get a random word from the dictionary
            word_data = db.get_random_word_for_ritual()
            
            if not word_data:
                logger.error("Failed to get a random word for ritual")
                return None
            
            # Get the word and its meaning
            word = word_data.get('word', '')
            meaning = word_data.get('meaning_ru', '')
            
            # Get user avatar for personalized content
            user_data = db.get_user(user_id)
            avatar = user_data.get('avatar') if user_data else None
            
            # Generate ritual text using OpenAI
            ritual_text = await openai_service.generate_word_ritual(word, meaning, avatar)
            
            # Format the ritual message
            message = f"🔮 **Ритуал словеси**\n\n"
            message += f"{ritual_text}"
            
            # Create keyboard with options
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔮 Получить новое заклинание", "callback_data": "get_word_ritual"}],
                    [{"text": "📖 Получить задание", "callback_data": "get_assignment"}],
                    [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
                ]
            }
            
            return {"message": message, "keyboard": keyboard}
            
        except Exception as e:
            logger.error(f"Error generating ritual message: {e}")
            return None
    
    async def send_daily_ritual_to_all_users(self):
        """Send daily ritual to all users who have allowed messages"""
        try:
            # Get all users from the database
            users = db.get_all_active_users()
            
            if not users:
                logger.info("No active users found")
                return
            
            logger.info(f"Sending daily ritual to {len(users)} users")
            
            # Send ritual to each user
            for user in users:
                user_id = user.get('user_id')
                
                # Generate personalized ritual message
                ritual_data = await self.generate_ritual_message(user_id)
                
                if not ritual_data:
                    continue
                
                # Send the message
                await self.send_message(
                    user_id, 
                    ritual_data["message"], 
                    ritual_data["keyboard"]
                )
                
                # Sleep a bit to avoid hitting Telegram API rate limits
                await asyncio.sleep(0.1)
            
            logger.info("Daily ritual sending completed")
            
        except Exception as e:
            logger.error(f"Error sending daily ritual: {e}")
    
    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()

async def main():
    """Main function to send daily rituals"""
    logger.info("Starting daily ritual sender")
    
    # Create sender instance
    sender = DailyRitualSender(TELEGRAM_BOT_TOKEN)
    
    try:
        # Send daily ritual to all users
        await sender.send_daily_ritual_to_all_users()
    finally:
        # Close the session
        await sender.close()
    
    logger.info("Daily ritual sender completed")

if __name__ == "__main__":
    asyncio.run(main())
