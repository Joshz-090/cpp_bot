from sqlalchemy.orm import Session
from ..models import User
from ..database import get_session

class LeaderboardService:
    @staticmethod
    def get_top_users(limit: int = 10) -> list[User]:
        """Queries the top users by score from the database."""
        with get_session() as session:
            # Efficiently queried thanks to index on 'score'
            return session.query(User).order_by(User.score.desc()).limit(limit).all()

    @staticmethod
    def format_leaderboard(users: list[User]) -> str:
        """Formats the leaderboard data into a readable list."""
        if not users:
            return "📈 *Leaderboard*\n\nNo scores recorded yet. Start a /quiz to be the first!"

            # Prioritize custom nickname for identity
            display_name = user.nickname if user.nickname else (user.username if user.username else user.full_name)
            if not display_name:
                display_name = f"User_{user.telegram_id}"
            
            streak_icon = " 🔥" if user.streak_count >= 3 else ""
            leaderboard_text += f"{i}. {display_name}{streak_icon} - {user.score} pts\n"
            
        return leaderboard_text
