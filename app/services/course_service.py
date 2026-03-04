from sqlalchemy.orm import Session
from ..models import WeeklyContent, Course, ContentFile
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
    def get_content_files(course_id: int, week_number: int, file_type: str = None):
        """Retrieves content files for a specific week and type."""
        with get_session() as session:
            content = session.query(WeeklyContent).filter(
                WeeklyContent.course_id == course_id,
                WeeklyContent.week_number == week_number
            ).first()
            
            if not content:
                return []
            
            query = session.query(ContentFile).filter(
                ContentFile.weekly_content_id == content.id
            )
            
            if file_type:
                query = query.filter(ContentFile.file_type == file_type)
                
            return query.all()

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
                session.flush()  # Get the ID
            
            for key, value in kwargs.items():
                if hasattr(content, key):
                    setattr(content, key, value)
            
            session.commit()
            return content

    @staticmethod
    def add_content_file(course_id: int, week_number: int, file_type: str, 
                        file_id: str = None, file_url: str = None, file_name: str = None):
        """Adds a new content file (PDF or video) to weekly content."""
        with get_session() as session:
            content = session.query(WeeklyContent).filter(
                WeeklyContent.course_id == course_id,
                WeeklyContent.week_number == week_number
            ).first()
            
            if not content:
                content = WeeklyContent(course_id=course_id, week_number=week_number)
                session.add(content)
                session.flush()
            
            new_file = ContentFile(
                weekly_content_id=content.id,
                file_type=file_type,
                file_id=file_id,
                file_url=file_url,
                file_name=file_name
            )
            session.add(new_file)
            session.commit()
            return new_file

    @staticmethod
    def remove_content_file(file_id: int):
        """Removes a content file by its ID."""
        with get_session() as session:
            file_obj = session.query(ContentFile).filter(ContentFile.id == file_id).first()
            if file_obj:
                session.delete(file_obj)
                session.commit()
                return True
            return False

    @staticmethod
    def list_content_files(course_id: int, week_number: int):
        """Lists all content files for a specific week."""
        with get_session() as session:
            content = session.query(WeeklyContent).filter(
                WeeklyContent.course_id == course_id,
                WeeklyContent.week_number == week_number
            ).first()
            
            if not content:
                return []
            
            return session.query(ContentFile).filter(
                ContentFile.weekly_content_id == content.id
            ).order_by(ContentFile.created_at).all()

    @staticmethod
    def get_content_file_by_id(file_id: int):
        """Gets a specific content file by ID."""
        with get_session() as session:
            return session.query(ContentFile).filter(ContentFile.id == file_id).first()
