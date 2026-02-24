#!/usr/bin/env python3
"""
Test script to verify the /quiz command fix
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.quiz_service import QuizService
from app.services.user_service import UserService
from app.handlers.student_handler import quizzes_command, check_user_registration
from unittest.mock import Mock, AsyncMock

async def test_quiz_fix():
    """Test the fixed quiz command"""
    print("🧪 Testing /quiz command fix...")
    
    # Test Case 1: Unregistered user
    print("\n1. Testing with unregistered user...")
    mock_update = Mock()
    mock_update.effective_user.id = 999999999  # Test user ID
    mock_update.effective_user.username = "unregistered_user"
    mock_update.effective_user.full_name = "Unregistered User"
    mock_update.message.reply_text = AsyncMock()
    
    mock_context = Mock()
    
    # Check registration status
    is_registered = await check_user_registration(mock_update, mock_context)
    print(f"   Registration check result: {is_registered}")
    
    if mock_update.message.reply_text.called:
        call_args = mock_update.message.reply_text.call_args
        print(f"   📝 Message sent: {call_args[0][0][:50]}...")
        print("   ✅ Unregistered user handled correctly")
    
    # Test Case 2: Registered user
    print("\n2. Testing with registered user...")
    mock_update2 = Mock()
    mock_update2.effective_user.id = 1238415224  # Known registered user ID
    mock_update2.effective_user.username = "Joshz_090"
    mock_update2.effective_user.full_name = "Eyasu"
    mock_update2.message.reply_text = AsyncMock()
    
    is_registered2 = await check_user_registration(mock_update2, mock_context)
    print(f"   Registration check result: {is_registered2}")
    
    if is_registered2:
        # Test the actual quiz command
        result = await quizzes_command(mock_update2, mock_context)
        print(f"   ✅ Quiz command executed successfully")
        print(f"   Returned state: {result}")
        
        if mock_update2.message.reply_text.called:
            call_args = mock_update2.message.reply_text.call_args
            print(f"   📝 Quiz menu sent: {call_args[0][0][:50]}...")
    
    # Test Case 3: User exists but not registered
    print("\n3. Testing with existing but unregistered user...")
    mock_update3 = Mock()
    mock_update3.effective_user.id = 6948253768  # Known existing but unregistered user
    mock_update3.effective_user.username = "Joshz_091"
    mock_update3.effective_user.full_name = "Josh"
    mock_update3.message.reply_text = AsyncMock()
    
    is_registered3 = await check_user_registration(mock_update3, mock_context)
    print(f"   Registration check result: {is_registered3}")
    
    if not is_registered3 and mock_update3.message.reply_text.called:
        call_args = mock_update3.message.reply_text.call_args
        print(f"   📝 Guidance message sent: {call_args[0][0][:50]}...")
        print("   ✅ Existing but unregistered user handled correctly")

if __name__ == "__main__":
    asyncio.run(test_quiz_fix())
