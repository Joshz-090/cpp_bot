import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars for validation bypass
os.environ["BOT_TOKEN"] = "12345678:ABCDEF"
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///test.db"

from app.database import init_db
from app.services.user_service import UserService
from app.services.quiz_service import QuizService
from app.models import DifficultyLevel

def verify_data_layer():
    print("--- Starting Data Layer Verification ---")
    
    # 1. Initialize DB
    print("Initializing database...")
    init_db()
    
    # 2. Add a course
    print("Creating course...")
    course = QuizService.get_or_create_course("C++ Basics", "Learn the fundamentals of C++ programming.")
    print(f"Course created: {course}")
    
    # 3. Add a user
    print("Creating user...")
    user = UserService.get_or_create_user(telegram_id=12345678, username="testuser", full_name="Test User")
    print(f"User created: {user}")
    
    # 4. Add a question
    print("Adding question...")
    question_data = {
        'difficulty': DifficultyLevel.EASY,
        'question_text': "What is the entry point of a C++ program?",
        'option_a': "start()",
        'option_b': "begin()",
        'option_c': "main()",
        'option_d': "init()",
        'correct_answer': "C",
        'explanation': "The main() function is the entry point of every C++ program."
    }
    question = QuizService.add_question(course.id, question_data)
    print(f"Question added: {question}")
    
    # 5. Submit an answer
    print("Submitting answer...")
    submission = QuizService.submit_answer(user.id, user.telegram_id, question.id, "C")
    print(f"Submission recorded: {submission}")
    
    # 6. Update score
    if submission.is_correct:
        print("Correct answer! Updating score...")
        updated_user = UserService.update_score(user.telegram_id, 10)
        print(f"Updated score: {updated_user.score}")
    
    # 7. Fetch Leaderboard
    print("Fetching leaderboard...")
    leaderboard = UserService.get_leaderboard()
    print(f"Leaderboard: {leaderboard}")
    
    print("\n--- Data Layer Verification Successful ---")

if __name__ == "__main__":
    # Ensure DATABASE_URL is set in environment for testing
    # For this verification, we use SQLite if Postgres is not configured
    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL not set. Using SQLite for verification.")
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
    
    try:
        verify_data_layer()
    finally:
        # Cleanup test db if created
        if os.path.exists("test.db"):
            # os.remove("test.db")
            pass
