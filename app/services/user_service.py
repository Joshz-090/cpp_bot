from sqlalchemy.orm import Session
from ..models import User, UserRole
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
