from sqlalchemy.orm import Session
from ..models import WeeklyContent, Course
from ..database import get_session

class CourseService:
    @staticmethod
    def get_all_courses():
        """Returns all available courses."""
        with get_session() as session:
            return session.query(Course).all()

    @staticmethod
    def get_course_by_name(name: str):
        """Retrieves a course by its name."""
        with get_session() as session:
            return session.query(Course).filter(Course.name == name).first()

    @staticmethod
    def get_weekly_content(course_id: int, week_number: int):
        """Retrieves content for a specific week of a course."""
        with get_session() as session:
            return session.query(WeeklyContent).filter(
                WeeklyContent.course_id == course_id,
                WeeklyContent.week_number == week_number
            ).first()

    @staticmethod
    def update_weekly_content(course_id: int, week_number: int, **kwargs):
        """Updates or creates weekly content."""
        with get_session() as session:
            content = session.query(WeeklyContent).filter(
                WeeklyContent.course_id == course_id,
                WeeklyContent.week_number == week_number
            ).first()
            
            if not content:
                content = WeeklyContent(course_id=course_id, week_number=week_number)
                session.add(content)
            
            for key, value in kwargs.items():
                if hasattr(content, key):
                    setattr(content, key, value)
            
            session.commit()
            return content
