from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import Question, Submission, Course, DifficultyLevel
from ..database import get_session
from typing import List, Optional

class QuizService:
    @staticmethod
    def get_random_question(user_id: int) -> Optional[Question]:
        """Fetches a random question that the user hasn't answered yet."""
        from sqlalchemy import func
        with get_session() as session:
            # Subquery for answered question IDs
            answered_subquery = session.query(Submission.question_id).filter(Submission.user_id == user_id).subquery()
            
            # Query for questions not in the answered subquery
            query = session.query(Question).filter(~Question.id.in_(answered_subquery))
            
            # Pick a random one
            return query.order_by(func.random()).first()

    @staticmethod
    def submit_answer(user_id: int, telegram_id: int, question_id: int, selected_answer: str) -> Submission:
        """Records a user's answer, checks correctness, and updates score."""
        from .user_service import UserService
        with get_session() as session:
            question = session.query(Question).filter(Question.id == question_id).first()
            if not question:
                raise ValueError("Question not found")

            is_correct = question.correct_answer.upper() == selected_answer.upper()
            
            submission = Submission(
                user_id=user_id,
                question_id=question_id,
                selected_answer=selected_answer,
                is_correct=is_correct
            )
            session.add(submission)
            
            if is_correct:
                # Update user score via session-bound object to ensure transaction safety
                from ..models import User
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.score += 1
            
            session.commit()
            session.refresh(submission)
            return submission

    @staticmethod
    def get_or_create_course(name: str, description: str = None) -> Course:
        """Retrieves a course by name or creates one if not found."""
        with get_session() as session:
            course = session.query(Course).filter(Course.name == name).first()
            if not course:
                course = Course(name=name, description=description)
                session.add(course)
                session.commit()
                session.refresh(course)
            return course

    @staticmethod
    def add_question(course_id: int, question_data: dict) -> Question:
        """Adds a new question to a course, optionally linked to a quiz."""
        with get_session() as session:
            question = Question(
                course_id=course_id,
                quiz_id=question_data.get('quiz_id'),
                difficulty=question_data.get('difficulty', DifficultyLevel.EASY),
                question_text=question_data['question_text'],
                option_a=question_data['option_a'],
                option_b=question_data['option_b'],
                option_c=question_data['option_c'],
                option_d=question_data['option_d'],
                correct_answer=question_data['correct_answer'],
                explanation=question_data.get('explanation')
            )
            session.add(question)
            session.commit()
            session.refresh(question)
            return question

    @staticmethod
    def create_quiz(title: str, description: str, duration: int, week: int, 
                    start_time: datetime = None, end_time: datetime = None) -> Quiz:
        """Creates a new structured quiz with optional availability window."""
        from ..models import Quiz
        with get_session() as session:
            quiz = Quiz(
                title=title,
                description=description,
                duration_minutes=duration,
                week_number=week,
                available_from=start_time,
                available_until=end_time
            )
            session.add(quiz)
            session.commit()
            session.refresh(quiz)
            return quiz

    @staticmethod
    def get_quizzes_by_week(week: int, include_expired: bool = False) -> List[Quiz]:
        """Fetches quizzes for a week. Students only see active ones."""
        from ..models import Quiz
        from datetime import datetime
        with get_session() as session:
            query = session.query(Quiz).filter(Quiz.week_number == week)
            
            if not include_expired:
                now = datetime.utcnow()
                # Quiz must have started (or no start set) AND not ended (or no end set)
                query = query.filter(
                    (Quiz.available_from <= now) | (Quiz.available_from == None),
                    (Quiz.available_until >= now) | (Quiz.available_until == None)
                )
            
            return query.all()

    @staticmethod
    def get_quiz(quiz_id: int) -> Optional[Quiz]:
        """Fetches a specific quiz by ID."""
        from ..models import Quiz
        with get_session() as session:
            return session.query(Quiz).filter(Quiz.id == quiz_id).first()

    @staticmethod
    def get_quiz_questions(quiz_id: int) -> List[Question]:
        """Fetches all questions for a specific quiz."""
        with get_session() as session:
            return session.query(Question).filter(Question.quiz_id == quiz_id).all()

    @staticmethod
    def start_quiz_attempt(user_id: int, quiz_id: int) -> QuizAttempt:
        """Starts a new quiz attempt for a user."""
        from ..models import QuizAttempt
        with get_session() as session:
            attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id)
            session.add(attempt)
            session.commit()
            session.refresh(attempt)
            return attempt

    @staticmethod
    def finish_quiz_attempt(attempt_id: int, final_score: int) -> Optional[QuizAttempt]:
        """Marks a quiz attempt as completed."""
        from ..models import QuizAttempt
        from datetime import datetime
        with get_session() as session:
            attempt = session.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
            if attempt:
                attempt.completed_at = datetime.utcnow()
                attempt.score = final_score
                session.commit()
                session.refresh(attempt)
            return attempt

    @staticmethod
    def get_quiz_leaderboard(quiz_id: int) -> List[dict]:
        """Fetches the leaderboard for a specific quiz, best attempt per user only."""
        from ..models import QuizAttempt, User, Question
        with get_session() as session:
            # Join attempts with users
            all_attempts = session.query(QuizAttempt, User).join(User, QuizAttempt.user_id == User.id)\
                .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.completed_at != None)\
                .order_by(QuizAttempt.score.desc(), (QuizAttempt.completed_at - QuizAttempt.started_at).asc())\
                .all()
            
            # Fetch quiz metadata for total questions
            quiz_questions_count = session.query(Question).filter(Question.quiz_id == quiz_id).count()
            
            leaderboard = []
            seen_users = set()
            
            for attempt, user in all_attempts:
                if user.id in seen_users:
                    continue
                seen_users.add(user.id)
                
                duration = (attempt.completed_at - attempt.started_at).total_seconds() / 60
                accuracy = (attempt.score / quiz_questions_count * 100) if quiz_questions_count > 0 else 0
                
                leaderboard.append({
                    'nickname': user.nickname,
                    'score': attempt.score,
                    'total': quiz_questions_count,
                    'accuracy': round(accuracy, 1),
                    'time_taken': round(duration, 1),
                    'streak': user.streak_count
                })
                
                if len(leaderboard) >= 10:
                    break
                    
            return leaderboard
