from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from .config import Config

# --- Database Engine Setup ---
# We use pooling for production readiness.
# pool_size: number of permanent connections
# max_overflow: number of additional connections that can be created during peak load
engine = create_engine(
    Config.DATABASE_URL,
    pool_size=20,     # Increased for 60+ concurrent students
    max_overflow=50,  # Allows up to 70 total connections during peaks
    pool_pre_ping=True
)

# --- Session Management ---
# SessionLocal is the factory for new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

# Base class for our ORM models
Base = declarative_base()

@contextmanager
def get_session():
    """Context manager for safe database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    """Initializes the database by creating all tables and seeding default data."""
    # This is safe to run multiple times; it won't recreate existing tables.
    Base.metadata.create_all(bind=engine)
    
    # Seed default courses
    from .models import Course
    with get_session() as session:
        default_courses = [
            {"name": "C++", "description": "C++ Programming course."},
            {"name": "Python", "description": "Python Programming course."},
            {"name": "Web Dev", "description": "Web Development course."}
        ]
        for c_data in default_courses:
            existing = session.query(Course).filter(Course.name == c_data["name"]).first()
            if not existing:
                course = Course(name=c_data["name"], description=c_data["description"])
                session.add(course)
        session.commit()
