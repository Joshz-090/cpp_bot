from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from ..models import User, UserRole, QuizAttempt, Submission, Feedback
from ..database import get_session

class UserService:
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, full_name: str = None) -> User:
        """Retrieves a user by telegram_id or creates one if not found."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name,
                    role=UserRole.STUDENT.value
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            else:
                # Update username or full name if they changed
                if username and user.username != username:
                    user.username = username
                if full_name and user.full_name != full_name:
                    user.full_name = full_name
                session.commit()
                session.refresh(user)
            return user

    @staticmethod
    def update_registration(telegram_id: int, nickname: str, password: str) -> bool:
        """Updates user nickname and password after onboarding."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.nickname = nickname
                user.password = password
                session.commit()
                return True
            return False

    @staticmethod
    def is_registered(telegram_id: int) -> bool:
        """Checks if a user has completed the onboarding registration."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            return user is not None and user.nickname is not None and user.password is not None

    @staticmethod
    def get_user_by_nickname(nickname: str) -> User:
        """Retrieves a user by their nickname."""
        with get_session() as session:
            return session.query(User).filter(User.nickname == nickname).first()

    @staticmethod
    def link_account(nickname: str, password: str, new_telegram_id: int) -> bool:
        """Links an existing account to a new telegram_id (Login/Migration)."""
        with get_session() as session:
            user = session.query(User).filter(
                User.nickname == nickname,
                User.password == password
            ).first()
            
            if user:
                # Update the ID to the new device/account
                # Note: We must check if the new_telegram_id is already associated with someone else
                existing_new = session.query(User).filter(User.telegram_id == new_telegram_id).first()
                if existing_new and existing_new.id != user.id:
                    # Delete the 'guest' user created by start handler if it exists
                    session.delete(existing_new)
                    session.flush()  # Ensure unique constraint is cleared before update
                
                user.telegram_id = new_telegram_id
                session.commit()
                return True
            return False

    @staticmethod
    def recover_password(telegram_id: int, telegram_username: str) -> str:
        """Returns the password if the telegram username matches the one in DB."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user and user.username == telegram_username:
                return user.password
            return None

    @staticmethod
    def update_score(telegram_id: int, points: int) -> User:
        """Updates the user's score by the given points."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.score += points
                session.commit()
                session.refresh(user)
            return user

    @staticmethod
    def get_leaderboard(limit: int = 10):
        """Returns the top users by score."""
        with get_session() as session:
            return session.query(User).order_by(User.score.desc()).limit(limit).all()

    @staticmethod
    def set_admin(telegram_id: int) -> bool:
        """Promotes a user to admin."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.role = UserRole.ADMIN.value
                session.commit()
                return True
            return False

    @staticmethod
    def is_admin(telegram_id: int) -> bool:
        """Checks if a user has admin rights."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            return user is not None and user.role == UserRole.ADMIN.value

    @staticmethod
    def get_all_users() -> list[User]:
        """Returns all registered users."""
        with get_session() as session:
            return session.query(User).all()

    @staticmethod
    def logout_user(telegram_id: int) -> bool:
        """Decouples a Telegram account from its nickname."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.telegram_id = None
                session.commit()
                return True
            return False

    @staticmethod
    def update_streak(telegram_id: int):
        """Increments or resets student daily streak."""
        from datetime import datetime, date
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return
            
            now = datetime.utcnow()
            today = now.date()
            
            if user.last_activity_at:
                last_active_date = user.last_activity_at.date()
                days_diff = (today - last_active_date).days
                
                if days_diff == 1:
                    user.streak_count += 1
                elif days_diff > 1:
                    user.streak_count = 1
                # if days_diff == 0, streak stays same (already active today)
            else:
                user.streak_count = 1
            
            user.last_activity_at = now
            session.commit()

    @staticmethod
    def add_badge(telegram_id: int, badge_code: str):
        """Adds a badge to the user's collection if they don't have it."""
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user: return
            
            current_badges = user.badges.split(',') if user.badges else []
            if badge_code not in current_badges:
                current_badges.append(badge_code)
                user.badges = ','.join(current_badges)
                session.commit()

    @staticmethod
    def get_user(telegram_id: int) -> User:
        """Retrieves a user by their Telegram ID."""
        with get_session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()

    @staticmethod
    def get_user_stats(user_id: int) -> dict:
        """Aggregates and returns performance metrics for a student."""
        with get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {}

            attempts = session.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).all()
            total_quizzes = len(attempts)
            
            # Simple aggregation for correctness
            total_correct = session.query(func.sum(QuizAttempt.score)).filter(QuizAttempt.user_id == user_id).scalar() or 0
            
            # Submissions for total possible (simplified calculation)
            total_questions = session.query(func.count(Submission.id)).filter(Submission.user_id == user_id).scalar() or 0
            
            avg_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
            
            # Calculate average time (simplified)
            avg_time = 0
            if total_quizzes > 0:
                times = []
                for a in attempts:
                    if a.completed_at and a.started_at:
                        times.append((a.completed_at - a.started_at).total_seconds() / 60)
                if times:
                    avg_time = sum(times) / len(times)

            return {
                'total_quizzes': total_quizzes,
                'total_correct': total_correct,
                'avg_accuracy': round(avg_accuracy, 1),
                'avg_time': round(avg_time, 1),
                'streak_count': user.streak_count
            }

    @staticmethod
    def get_overall_leaderboard(limit: int = 10):
        """Returns consolidated leaderboard data for the top students."""
        with get_session() as session:
            top_users = session.query(User).order_by(User.score.desc()).limit(limit).all()
            leaderboard = []
            for user in top_users:
                stats = UserService.get_user_stats(user.id)
                leaderboard.append({
                    'nickname': user.nickname or user.full_name or "Anonymous",
                    'total_quizzes': stats.get('total_quizzes', 0),
                    'avg_accuracy': stats.get('avg_accuracy', 0),
                    'streak_count': user.streak_count,
                    'score': user.score
                })
            return leaderboard

    @staticmethod
    def add_feedback(user_id: int, content: str):
        """Adds a new feedback entry for a user."""
        with get_session() as session:
            feedback = Feedback(user_id=user_id, content=content)
            session.add(feedback)
            session.commit()

    @staticmethod
    def get_all_feedback():
        """Returns all feedback entries, ordered by newest first."""
        with get_session() as session:
            return session.query(Feedback).options(joinedload(Feedback.user)).order_by(Feedback.created_at.desc()).all()
