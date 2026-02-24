#!/usr/bin/env python3
"""
Test script for quiz and question management interface
"""

import asyncio
import sys
import os

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.handlers.admin_handler import (
    start_manage_quizzes,
    manage_quiz_select_week,
    manage_quiz_actions,
    edit_quiz_info,
    process_quiz_edit,
    delete_quiz,
    confirm_delete_quiz,
    start_manage_questions,
    manage_question_actions,
    edit_question,
    process_question_edit,
    delete_question,
    confirm_delete_question,
    handle_management_back
)
from unittest.mock import Mock, AsyncMock

async def test_management_interface():
    """Test the complete management interface"""
    print("🧪 Testing Quiz and Question Management Interface...")
    
    # Test 1: Start quiz management
    print("\n1. Testing start_manage_quizzes...")
    mock_update = Mock()
    mock_update.callback_query = Mock()
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.message = Mock()
    mock_update.callback_query.message.reply_text = AsyncMock()
    mock_update.callback_query.data = "admin_manage_quizzes"
    
    mock_context = Mock()
    mock_context.user_data = {}
    
    try:
        result = await start_manage_quizzes(mock_update, mock_context)
        print(f"   ✅ Quiz management started")
        print(f"   Returned state: {result}")
        
        if mock_update.callback_query.message.reply_text.called:
            call_args = mock_update.callback_query.message.reply_text.call_args
            print(f"   📝 Week selection displayed: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Quiz week selection
    print("\n2. Testing manage_quiz_select_week...")
    mock_update2 = Mock()
    mock_update2.callback_query = Mock()
    mock_update2.callback_query.answer = AsyncMock()
    mock_update2.callback_query.edit_message_text = AsyncMock()
    mock_update2.callback_query.data = "mg_quiz_week_1"
    
    mock_context2 = Mock()
    mock_context2.user_data = {}
    
    try:
        result2 = await manage_quiz_select_week(mock_update2, mock_context2)
        print(f"   ✅ Week selection handled")
        print(f"   Returned state: {result2}")
        print(f"   Selected week: {mock_context2.user_data.get('mg_week')}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Quiz actions
    print("\n3. Testing manage_quiz_actions...")
    mock_update3 = Mock()
    mock_update3.callback_query = Mock()
    mock_update3.callback_query.answer = AsyncMock()
    mock_update3.callback_query.edit_message_text = AsyncMock()
    mock_update3.callback_query.data = "mg_quiz_actions_1"
    
    mock_context3 = Mock()
    mock_context3.user_data = {'mg_week': 1}
    
    # Mock quiz object
    from unittest.mock import MagicMock
    mock_quiz = MagicMock()
    mock_quiz.title = "Test Quiz"
    mock_quiz.description = "Test Description"
    mock_quiz.week_number = 1
    mock_quiz.duration_minutes = 15
    mock_quiz.available_from = True
    mock_quiz.available_until = True
    
    try:
        result3 = await manage_quiz_actions(mock_update3, mock_context3)
        print(f"   ✅ Quiz actions displayed")
        print(f"   Returned state: {result3}")
        
        if mock_update3.callback_query.edit_message_text.called:
            call_args = mock_update3.callback_query.edit_message_text.call_args
            print(f"   📝 Actions menu displayed: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Edit quiz info
    print("\n4. Testing edit_quiz_info...")
    mock_update4 = Mock()
    mock_update4.callback_query = Mock()
    mock_update4.callback_query.answer = AsyncMock()
    mock_update4.callback_query.edit_message_text = AsyncMock()
    mock_update4.callback_query.data = "mg_edit_quiz_info"
    
    mock_context4 = Mock()
    mock_context4.user_data = {'mg_quiz': mock_quiz}
    
    try:
        result4 = await edit_quiz_info(mock_update4, mock_context4)
        print(f"   ✅ Quiz edit started")
        print(f"   Returned state: {result4}")
        
        if mock_update4.callback_query.edit_message_text.called:
            call_args = mock_update4.callback_query.edit_message_text.call_args
            print(f"   📝 Edit interface displayed: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Question management
    print("\n5. Testing start_manage_questions...")
    mock_update5 = Mock()
    mock_update5.callback_query = Mock()
    mock_update5.callback_query.answer = AsyncMock()
    mock_update5.callback_query.message = Mock()
    mock_update5.callback_query.message.reply_text = AsyncMock()
    mock_update5.callback_query.data = "admin_manage_questions"
    
    mock_context5 = Mock()
    mock_context5.user_data = {}
    
    try:
        result5 = await start_manage_questions(mock_update5, mock_context5)
        print(f"   ✅ Question management started")
        print(f"   Returned state: {result5}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 6: Question actions
    print("\n6. Testing manage_question_actions...")
    mock_update6 = Mock()
    mock_update6.callback_query = Mock()
    mock_update6.callback_query.answer = AsyncMock()
    mock_update6.callback_query.edit_message_text = AsyncMock()
    mock_update6.callback_query.data = "mg_question_actions_1"
    
    mock_context6 = Mock()
    mock_context6.user_data = {}
    
    # Mock question object
    mock_question = MagicMock()
    mock_question.question_text = "What is 2+2?"
    mock_question.option_a = "3"
    mock_question.option_b = "4"
    mock_question.option_c = "5"
    mock_question.option_d = "6"
    mock_question.correct_answer = "A"
    
    try:
        result6 = await manage_question_actions(mock_update6, mock_context6)
        print(f"   ✅ Question actions displayed")
        print(f"   Returned state: {result6}")
        
        if mock_update6.callback_query.edit_message_text.called:
            call_args = mock_update6.callback_query.edit_message_text.call_args
            print(f"   📝 Question actions displayed: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 7: Edit question
    print("\n7. Testing edit_question...")
    mock_update7 = Mock()
    mock_update7.callback_query = Mock()
    mock_update7.callback_query.answer = AsyncMock()
    mock_update7.callback_query.edit_message_text = AsyncMock()
    mock_update7.callback_query.data = "mg_edit_question"
    
    mock_context7 = Mock()
    mock_context7.user_data = {'mg_question': mock_question}
    
    try:
        result7 = await edit_question(mock_update7, mock_context7)
        print(f"   ✅ Question edit started")
        print(f"   Returned state: {result7}")
        
        if mock_update7.callback_query.edit_message_text.called:
            call_args = mock_update7.callback_query.edit_message_text.call_args
            print(f"   📝 Edit interface displayed: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 8: Back navigation
    print("\n8. Testing handle_management_back...")
    mock_update8 = Mock()
    mock_update8.callback_query = Mock()
    mock_update8.callback_query.answer = AsyncMock()
    mock_update8.callback_query.edit_message_text = AsyncMock()
    mock_update8.callback_query.data = "mg_quiz_back"
    
    mock_context8 = Mock()
    mock_context8.user_data = {}
    
    try:
        result8 = await handle_management_back(mock_update8, mock_context8)
        print(f"   ✅ Back navigation handled")
        print(f"   Returned state: {result8}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_management_interface())
