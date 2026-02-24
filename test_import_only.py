#!/usr/bin/env python3
"""
Test import only to isolate the syntax error
"""

import sys
import os

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

try:
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
    print("✅ Import successful!")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
