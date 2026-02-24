#!/usr/bin/env python3
"""
Debug script to test the /quiz command functionality
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.quiz_service import QuizService
from app.services.user_service import UserService
from app.handlers.student_handler import quizzes_command
from unittest.mock import Mock, AsyncMock

async def debug_quiz_command():
    """Debug the quiz command step by step"""
    print("🔍 Debugging /quiz command...")
    
    # Mock Update and Context objects
    mock_update = Mock()
    mock_update.effective_user.id = 123456789  # Test user ID
    mock_update.message.reply_text = AsyncMock()
    
    mock_context = Mock()
    
    # Step 1: Check if user is registered
    print("\n1. Checking user registration...")
    is_registered = UserService.is_registered(mock_update.effective_user.id)
    print(f"   User registered: {is_registered}")
    
    if not is_registered:
        print("   ❌ User not registered - this would cause the command to fail")
        # Create a test user
        user = UserService.get_or_create_user(
            telegram_id=mock_update.effective_user.id,
            username="test_user",
            full_name="Test User"
        )
        # Update registration
        UserService.update_registration(
            telegram_id=mock_update.effective_user.id,
            nickname="testnick",
            password="testpass"
        )
        print("   ✅ Created test user")
        is_registered = UserService.is_registered(mock_update.effective_user.id)
        print(f"   User now registered: {is_registered}")
    
    # Step 2: Test the quizzes_command function
    print("\n2. Testing quizzes_command function...")
    try:
        result = await quizzes_command(mock_update, mock_context)
        print(f"   ✅ quizzes_command executed successfully")
        print(f"   Returned state: {result}")
        
        # Check if reply_text was called
        if mock_update.message.reply_text.called:
            call_args = mock_update.message.reply_text.call_args
            print(f"   📝 Reply text: {call_args[0][0][:100]}...")
        else:
            print("   ❌ No reply sent")
            
    except Exception as e:
        print(f"   ❌ Error in quizzes_command: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Check available quizzes
    print("\n3. Checking available quizzes...")
    try:
        quizzes = QuizService.get_quizzes_by_week(1)
        print(f"   Found {len(quizzes)} quizzes for week 1")
        for quiz in quizzes:
            print(f"   - {quiz.title} (ID: {quiz.id})")
    except Exception as e:
        print(f"   ❌ Error fetching quizzes: {e}")
    
    # Step 4: Test quiz questions
    print("\n4. Testing quiz questions...")
    try:
        if quizzes:
            questions = QuizService.get_quiz_questions(quizzes[0].id)
            print(f"   Found {len(questions)} questions for quiz '{quizzes[0].title}'")
        else:
            print("   No quizzes to test questions")
    except Exception as e:
        print(f"   ❌ Error fetching questions: {e}")

if __name__ == "__main__":
    asyncio.run(debug_quiz_command())
