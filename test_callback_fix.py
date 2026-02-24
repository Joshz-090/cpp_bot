#!/usr/bin/env python3
"""
Test script to verify the callback query fix
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.quiz_service import QuizService
from app.services.user_service import UserService
from app.handlers.student_handler import std_quiz_info, show_week_selection
from unittest.mock import Mock, AsyncMock

async def test_callback_fix():
    """Test the callback query fix"""
    print("🧪 Testing callback query fix...")
    
    # Mock callback query for "back_to_weeks"
    print("\n1. Testing 'back to weeks' navigation...")
    mock_update = Mock()
    mock_update.callback_query = Mock()
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    mock_update.callback_query.data = "back_to_weeks"
    
    mock_context = Mock()
    mock_context.user_data = {}  # Make user_data a dict
    
    try:
        result = await std_quiz_info(mock_update, mock_context)
        print(f"   ✅ std_quiz_info handled 'back_to_weeks' successfully")
        print(f"   Returned state: {result}")
        
        # Check if edit_message_text was called
        if mock_update.callback_query.edit_message_text.called:
            call_args = mock_update.callback_query.edit_message_text.call_args
            print(f"   📝 Week selection displayed: {call_args[0][0][:50]}...")
        
    except Exception as e:
        print(f"   ❌ Error in std_quiz_info: {e}")
        import traceback
        traceback.print_exc()
    
    # Test direct show_week_selection function
    print("\n2. Testing show_week_selection function...")
    mock_update2 = Mock()
    mock_update2.callback_query = Mock()
    mock_update2.callback_query.answer = AsyncMock()
    mock_update2.callback_query.edit_message_text = AsyncMock()
    
    mock_context2 = Mock()
    mock_context2.user_data = {}  # Make user_data a dict
    
    try:
        result2 = await show_week_selection(mock_update2, mock_context2)
        print(f"   ✅ show_week_selection executed successfully")
        print(f"   Returned state: {result2}")
        
        if mock_update2.callback_query.edit_message_text.called:
            call_args = mock_update2.callback_query.edit_message_text.call_args
            print(f"   📝 Week selection UI displayed: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error in show_week_selection: {e}")
        import traceback
        traceback.print_exc()
    
    # Test normal quiz info display
    print("\n3. Testing normal quiz info display...")
    mock_update3 = Mock()
    mock_update3.callback_query = Mock()
    mock_update3.callback_query.answer = AsyncMock()
    mock_update3.callback_query.edit_message_text = AsyncMock()
    mock_update3.callback_query.data = "std_quiz_1"  # Quiz ID 1
    
    mock_context3 = Mock()
    mock_context3.user_data = {}  # Make user_data a dict
    
    try:
        result3 = await std_quiz_info(mock_update3, mock_context3)
        print(f"   ✅ Quiz info displayed successfully")
        print(f"   Returned state: {result3}")
        
    except Exception as e:
        print(f"   ❌ Error displaying quiz info: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_callback_fix())
