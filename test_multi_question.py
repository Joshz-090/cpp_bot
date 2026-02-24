#!/usr/bin/env python3
"""
Test script for multi-question admin functionality
"""

import asyncio
import sys
import os

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.handlers.admin_handler import (
    start_add_multiple, 
    multi_select_week, 
    multi_select_quiz, 
    collect_multiple_questions,
    save_multiple_questions
)
from unittest.mock import Mock, AsyncMock

async def test_multi_question_flow():
    """Test the complete multi-question addition flow"""
    print("🧪 Testing Multi-Question Admin Interface...")
    
    # Test 1: Start multi-question addition
    print("\n1. Testing start_add_multiple...")
    mock_update = Mock()
    mock_update.callback_query = Mock()
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.message = Mock()
    mock_update.callback_query.message.reply_text = AsyncMock()
    mock_update.callback_query.data = "admin_add_multiple"
    
    mock_context = Mock()
    mock_context.user_data = {}
    
    try:
        result = await start_add_multiple(mock_update, mock_context)
        print(f"   ✅ Multi-question addition started")
        print(f"   Returned state: {result}")
        
        if mock_update.callback_query.message.reply_text.called:
            call_args = mock_update.callback_query.message.reply_text.call_args
            print(f"   📝 Instructions sent: {call_args[0][0][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Week selection
    print("\n2. Testing multi_select_week...")
    mock_update2 = Mock()
    mock_update2.callback_query = Mock()
    mock_update2.callback_query.answer = AsyncMock()
    mock_update2.callback_query.message = Mock()
    mock_update2.callback_query.message.reply_text = AsyncMock()
    mock_update2.callback_query.data = "multi_week_1"
    
    mock_context2 = Mock()
    mock_context2.user_data = {}
    
    try:
        result2 = await multi_select_week(mock_update2, mock_context2)
        print(f"   ✅ Week selection handled")
        print(f"   Returned state: {result2}")
        print(f"   Selected week: {mock_context2.user_data.get('multi_week')}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Quiz selection
    print("\n3. Testing multi_select_quiz...")
    mock_update3 = Mock()
    mock_update3.callback_query = Mock()
    mock_update3.callback_query.answer = AsyncMock()
    mock_update3.callback_query.message = Mock()
    mock_update3.callback_query.message.reply_text = AsyncMock()
    mock_update3.callback_query.data = "multi_quiz_1"
    
    mock_context3 = Mock()
    mock_context3.user_data = {'multi_week': 1}
    
    try:
        result3 = await multi_select_quiz(mock_update3, mock_context3)
        print(f"   ✅ Quiz selection handled")
        print(f"   Returned state: {result3}")
        print(f"   Selected quiz ID: {mock_context3.user_data.get('multi_quiz_id')}")
        
        if mock_update3.callback_query.message.reply_text.called:
            call_args = mock_update3.callback_query.message.reply_text.call_args
            instructions = call_args[0][0]
            if "Please enter questions in this format" in instructions:
                print(f"   ✅ Instructions displayed correctly")
            else:
                print(f"   ⚠️ Instructions may be incomplete")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Question collection
    print("\n4. Testing collect_multiple_questions...")
    mock_update4 = Mock()
    mock_update4.message = Mock()
    mock_update4.message.text = "1) What is 2+2?\nA: 3\nB: 4\nC: 5\nD: 6\nthe correct answer? (A, B, C, or D)"
    mock_update4.message.reply_text = AsyncMock()
    
    mock_context4 = Mock()
    mock_context4.user_data = {
        'multi_questions': [],
        'current_question_num': 1,
        'multi_quiz_id': 1
    }
    
    try:
        result4 = await collect_multiple_questions(mock_update4, mock_context4)
        print(f"   ✅ Question collection started")
        print(f"   Returned state: {result4}")
        
        if mock_update4.message.reply_text.called:
            call_args = mock_update4.message.reply_text.call_args
            print(f"   📝 Response: {call_args[0][0][:50]}...")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Complete question
    print("\n5. Testing complete question parsing...")
    mock_update5 = Mock()
    mock_update5.message = Mock()
    mock_update5.message.text = "What is 2+2?\nA: 3\nB: 4\nC: 5\nD: 6\nthe correct answer? (A, B, C, or D)"
    mock_update5.message.reply_text = AsyncMock()
    
    mock_context5 = Mock()
    mock_context5.user_data = {
        'multi_questions': [],
        'current_q_data': {
            'number': 1,
            'raw_text': "1) What is 2+2?\nA: 3\nB: 4\nC: 5\nD: 6\nthe correct answer? (A, B, C, or D)"
        },
        'multi_quiz_id': 1
    }
    
    try:
        result5 = await collect_multiple_questions(mock_update5, mock_context5)
        print(f"   ✅ Complete question parsed")
        print(f"   Returned state: {result5}")
        
        # Check if question was saved
        if len(mock_context5.user_data['multi_questions']) > 0:
            q = mock_context5.user_data['multi_questions'][0]
            print(f"   ✅ Question saved: {q.get('question_text', '')[:30]}...")
            print(f"   ✅ Options: {list(q.get('options', {}).keys())}")
            print(f"   ✅ Correct answer: {q.get('correct_answer')}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 6: Done command
    print("\n6. Testing 'done' command...")
    mock_update6 = Mock()
    mock_update6.message = Mock()
    mock_update6.message.text = "done"
    mock_update6.message.reply_text = AsyncMock()
    
    mock_context6 = Mock()
    mock_context6.user_data = {
        'multi_questions': [{
            'question_text': 'What is 2+2?',
            'options': {'A': '3', 'B': '4', 'C': '5', 'D': '6'},
            'correct_answer': 'A'
        }],
        'multi_quiz_id': 1
    }
    
    try:
        result6 = await collect_multiple_questions(mock_update6, mock_context6)
        print(f"   ✅ 'Done' command handled")
        print(f"   Should trigger save_multiple_questions")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multi_question_flow())
