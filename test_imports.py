#!/usr/bin/env python3

# Test script to check telegram imports
try:
    print("Testing telegram imports...")
    
    # Try different import patterns
    try:
        from telegram import Update
        print("✅ telegram.Update import successful")
    except ImportError as e:
        print(f"❌ telegram.Update failed: {e}")
    
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        print("✅ InlineKeyboard imports successful")
    except ImportError as e:
        print(f"❌ InlineKeyboard imports failed: {e}")
    
    try:
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler
        print("✅ telegram.ext imports successful")
    except ImportError as e:
        print(f"❌ telegram.ext imports failed: {e}")
    
    try:
        from telegram.constants import ParseMode
        print("✅ ParseMode import successful")
    except ImportError as e:
        print(f"❌ ParseMode import failed: {e}")
    
    # Check what's actually available
    import telegram
    print(f"Telegram module location: {telegram.__file__}")
    print(f"Available in telegram module: {[attr for attr in dir(telegram) if not attr.startswith('_')]}")
    
except Exception as e:
    print(f"General error: {e}")