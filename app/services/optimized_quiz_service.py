from __future__ import annotations
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio
import logging

from sqlalchemy.orm import Session
from ..models import Question, Submission, Quiz, QuizAttempt, User
from ..database import get_session

logger = logging.getLogger(__name__)

@dataclass
class QuizSession:
    """In-memory quiz session data structure"""
    user_id: int
    telegram_id: int
    quiz_id: int
    attempt_id: int
    questions: List[Dict[str, Any]]
    current_index: int = 0
    score: int = 0
    started_at: datetime = None
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.utcnow()
        if self.expires_at is None:
            self.expires_at = self.started_at + timedelta(minutes=15)  # Default 15 min
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @property
    def current_question(self) -> Optional[Dict[str, Any]]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None
    
    @property
    def is_completed(self) -> bool:
        return self.current_index >= len(self.questions)
    
    def get_progress(self) -> tuple[int, int]:
        """Returns (current_question, total_questions)"""
        return (self.current_index + 1, len(self.questions))

class QuizSessionManager:
    """Thread-safe session manager for active quiz sessions"""
    _sessions: Dict[int, QuizSession] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def create_session(cls, user_id: int, telegram_id: int, quiz_id: int) -> QuizSession:
        """Create and store a new quiz session with pre-fetched questions"""
        async with cls._lock:
            # Clean expired sessions first
            await cls._cleanup_expired_sessions()
            
            # Check if user already has active session
            if user_id in cls._sessions:
                existing = cls._sessions[user_id]
                if not existing.is_expired:
                    return existing
                else:
                    del cls._sessions[user_id]
            
            # Fetch quiz questions in single query
            questions = await cls._fetch_quiz_questions_optimized(quiz_id)
            if not questions:
                raise ValueError("No questions found for this quiz")
            
            # Create quiz attempt record
            attempt = await cls._create_quiz_attempt(user_id, quiz_id)
            
            # Create session
            session = QuizSession(
                user_id=user_id,
                telegram_id=telegram_id,
                quiz_id=quiz_id,
                attempt_id=attempt.id,
                questions=questions
            )
            
            cls._sessions[user_id] = session
            logger.info(f"Created quiz session for user {user_id}, quiz {quiz_id}")
            return session
    
    @classmethod
    async def get_session(cls, user_id: int) -> Optional[QuizSession]:
        """Retrieve active session for user"""
        async with cls._lock:
            session = cls._sessions.get(user_id)
            if session and session.is_expired:
                await cls._commit_session_results(session)
                del cls._sessions[user_id]
                return None
            return session
    
    @classmethod
    async def update_session(cls, user_id: int, **kwargs) -> Optional[QuizSession]:
        """Update session parameters"""
        async with cls._lock:
            session = cls._sessions.get(user_id)
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
            return session
    
    @classmethod
    async def remove_session(cls, user_id: int) -> Optional[QuizSession]:
        """Remove and commit session results"""
        async with cls._lock:
            session = cls._sessions.pop(user_id, None)
            if session:
                await cls._commit_session_results(session)
            return session
    
    @classmethod
    async def _cleanup_expired_sessions(cls):
        """Remove expired sessions and commit their results"""
        expired_users = [
            user_id for user_id, session in cls._sessions.items() 
            if session.is_expired
        ]
        
        for user_id in expired_users:
            session = cls._sessions.pop(user_id)
            await cls._commit_session_results(session)
    
    @classmethod
    async def _fetch_quiz_questions_optimized(cls, quiz_id: int) -> List[Dict[str, Any]]:
        """Single query to fetch all quiz questions with options"""
        loop = asyncio.get_event_loop()
        
        def fetch_questions():
            with get_session() as session:
                questions = session.query(Question).filter(Question.quiz_id == quiz_id).all()
                return [
                    {
                        'id': q.id,
                        'question_text': q.question_text,
                        'option_a': q.option_a,
                        'option_b': q.option_b,
                        'option_c': q.option_c,
                        'option_d': q.option_d,
                        'correct_answer': q.correct_answer,
                        'explanation': q.explanation,
                        'difficulty': q.difficulty
                    }
                    for q in questions
                ]
        
        return await loop.run_in_executor(None, fetch_questions)
    
    @classmethod
    async def _create_quiz_attempt(cls, user_id: int, quiz_id: int) -> QuizAttempt:
        """Create quiz attempt record"""
        loop = asyncio.get_event_loop()
        
        def create_attempt():
            with get_session() as session:
                attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id)
                session.add(attempt)
                session.commit()
                session.refresh(attempt)
                return attempt
        
        return await loop.run_in_executor(None, create_attempt)
    
    @classmethod
    async def _commit_session_results(cls, session: QuizSession):
        """Batch commit all session results to database"""
        if not session:
            return
            
        loop = asyncio.get_event_loop()
        
        def commit_results():
            with get_session() as db_session:
                try:
                    # Update quiz attempt with final score and completion time
                    attempt = db_session.query(QuizAttempt).filter(
                        QuizAttempt.id == session.attempt_id
                    ).first()
                    
                    if attempt:
                        attempt.score = session.score
                        attempt.completed_at = datetime.utcnow()
                        
                        # Create all submissions in batch
                        submissions = []
                        for i, question in enumerate(session.questions[:session.current_index]):
                            # Get user's answer from session (you'd need to track this)
                            # For now, we'll create placeholder submissions
                            # In real implementation, you'd track selected answers
                            pass
                        
                        # Update user score
                        user = db_session.query(User).filter(User.id == session.user_id).first()
                        if user:
                            user.score += session.score
                            user.last_activity_at = datetime.utcnow()
                        
                        db_session.commit()
                        logger.info(f"Committed session results for user {session.user_id}")
                        
                except Exception as e:
                    logger.error(f"Error committing session results: {e}")
                    db_session.rollback()
        
        await loop.run_in_executor(None, commit_results)

class OptimizedQuizService:
    """High-performance quiz service with session caching"""
    
    @staticmethod
    async def start_quiz_session(user_id: int, telegram_id: int, quiz_id: int) -> QuizSession:
        """Initialize a new quiz session with pre-fetched questions"""
        return await QuizSessionManager.create_session(user_id, telegram_id, quiz_id)
    
    @staticmethod
    async def get_active_session(user_id: int) -> Optional[QuizSession]:
        """Get user's active quiz session"""
        return await QuizSessionManager.get_session(user_id)
    
    @staticmethod
    async def submit_answer_in_session(user_id: int, selected_answer: str) -> Dict[str, Any]:
        """Submit answer using cached session data for immediate feedback"""
        session = await QuizSessionManager.get_session(user_id)
        if not session:
            raise ValueError("No active quiz session found")
        
        if session.is_expired:
            await QuizSessionManager.remove_session(user_id)
            raise ValueError("Quiz session has expired")
        
        current_question = session.current_question
        if not current_question:
            raise ValueError("No current question available")
        
        # Check answer using cached data
        is_correct = current_question['correct_answer'].upper() == selected_answer.upper()
        
        # Update session state
        if is_correct:
            session.score += 1
        
        # Store answer for later batch commit
        # In real implementation, you'd track this in the session
        session.current_index += 1
        
        # Update session manager
        await QuizSessionManager.update_session(user_id, 
                                               score=session.score,
                                               current_index=session.current_index)
        
        # Check if quiz is completed
        if session.is_completed:
            await QuizSessionManager.remove_session(user_id)
            return {
                'is_correct': is_correct,
                'explanation': current_question.get('explanation'),
                'quiz_completed': True,
                'final_score': session.score,
                'total_questions': len(session.questions)
            }
        
        return {
            'is_correct': is_correct,
            'explanation': current_question.get('explanation'),
            'quiz_completed': False,
            'next_question': session.current_question,
            'progress': session.get_progress()
        }
    
    @staticmethod
    async def get_current_question(user_id: int) -> Optional[Dict[str, Any]]:
        """Get current question from cached session"""
        session = await QuizSessionManager.get_session(user_id)
        if not session or session.is_expired:
            return None
        
        return {
            'question': session.current_question,
            'progress': session.get_progress(),
            'time_remaining': max(0, (session.expires_at - datetime.utcnow()).total_seconds())
        }
    
    @staticmethod
    async def force_complete_session(user_id: int) -> Optional[Dict[str, Any]]:
        """Force complete a session (e.g., timeout or user cancellation)"""
        session = await QuizSessionManager.remove_session(user_id)
        if not session:
            return None
        
        return {
            'final_score': session.score,
            'total_questions': len(session.questions),
            'questions_answered': session.current_index,
            'time_taken': (datetime.utcnow() - session.started_at).total_seconds()
        }

class AdminMiddleware:
    """Middleware for admin authorization checks"""
    
    @staticmethod
    async def verify_admin_role(telegram_id: int) -> bool:
        """Verify user has admin role using cached data or database"""
        loop = asyncio.get_event_loop()
        
        def check_admin():
            with get_session() as session:
                user = session.query(User).filter(User.telegram_id == telegram_id).first()
                return user is not None and user.role == 'admin'
        
        return await loop.run_in_executor(None, check_admin)
    
    @staticmethod
    async def verify_admin_or_chat_admin(update, context) -> bool:
        """Verify admin role via database or Telegram chat member status"""
        telegram_id = update.effective_user.id
        
        # First check database role
        is_db_admin = await AdminMiddleware.verify_admin_role(telegram_id)
        if is_db_admin:
            return True
        
        # Fallback to Telegram chat admin check
        try:
            chat_member = await context.bot.get_chat_member(
                chat_id=update.effective_chat.id,
                user_id=telegram_id
            )
            return chat_member.status in ['administrator', 'creator']
        except Exception as e:
            logger.warning(f"Failed to check Telegram admin status: {e}")
            return False

# Utility function for async database operations
async def execute_async_db_operation(operation_func, *args, **kwargs):
    """Execute synchronous database operations asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, operation_func, *args, **kwargs)
