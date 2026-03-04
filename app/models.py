from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"

class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    nickname = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=True)
    role = Column(String, default=UserRole.STUDENT.value)  # Default role is student
    score = Column(Integer, default=0, index=True)
    streak_count = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)
    badges = Column(String, nullable=True) # Stored as comma-separated tags
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submissions = relationship("Submission", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}', role='{self.role}')>"

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    questions = relationship("Question", back_populates="course")

    def __repr__(self):
        return f"<Course(id={self.id}, name='{self.name}')>"

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    difficulty = Column(String, default=DifficultyLevel.EASY)
    question_text = Column(Text, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_answer = Column(String(1), nullable=False)  # A, B, C, or D
    explanation = Column(Text, nullable=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=True)

    # Relationships
    course = relationship("Course", back_populates="questions")
    submissions = relationship("Submission", back_populates="question")
    quiz = relationship("Quiz", back_populates="questions")

    def __repr__(self):
        return f"<Question(id={self.id}, difficulty='{self.difficulty}')>"

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_answer = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="submissions")
    question = relationship("Question", back_populates="submissions")

    def __repr__(self):
        return f"<Submission(id={self.id}, user_id={self.user_id}, is_correct={self.is_correct})>"

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=15)
    week_number = Column(Integer, index=True)
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    questions = relationship("Question", back_populates="quiz")
    attempts = relationship("QuizAttempt", back_populates="quiz")

    def __repr__(self):
        return f"<Quiz(id={self.id}, title='{self.title}', week={self.week_number})>"

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    score = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User") # No direct backref needed for now
    quiz = relationship("Quiz", back_populates="attempts")

    def __repr__(self):
        return f"<QuizAttempt(id={self.id}, user_id={self.user_id}, quiz_id={self.quiz_id})>"

class Feedback(Base):
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id})>"

class WeeklyContent(Base):
    __tablename__ = "weekly_content"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    week_number = Column(Integer, nullable=False)
    pdf_file_id = Column(String, nullable=True) # Telegram file_id or link (legacy)
    video_link = Column(String, nullable=True) # Legacy single video
    web_link = Column(String, nullable=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    course = relationship("Course")
    quiz = relationship("Quiz")
    pdf_files = relationship("ContentFile", back_populates="weekly_content", 
                              foreign_keys="ContentFile.weekly_content_id")
    video_files = relationship("ContentFile", back_populates="weekly_content",
                              foreign_keys="ContentFile.weekly_content_id")

    def __repr__(self):
        return f"<WeeklyContent(id={self.id}, course_id={self.course_id}, week={self.week_number})>"


class ContentFile(Base):
    __tablename__ = "content_files"
    
    id = Column(Integer, primary_key=True, index=True)
    weekly_content_id = Column(Integer, ForeignKey("weekly_content.id"), nullable=False)
    file_type = Column(String, nullable=False)  # 'pdf' or 'video'
    file_id = Column(String, nullable=True)     # Telegram file_id for PDFs
    file_url = Column(String, nullable=True)    # URL for videos or external PDFs
    file_name = Column(String, nullable=True)    # Original filename
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    weekly_content = relationship("WeeklyContent", back_populates="pdf_files")
    
    def __repr__(self):
        return f"<ContentFile(id={self.id}, type={self.file_type}, content_id={self.weekly_content_id})>"
