from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
# from sqlalchemy.ext.declarative import declarative_base



Base = declarative_base()

class User(Base):
    __tablename__ = 'users'    
    id = Column(Integer, primary_key=True)    
    # role = Column(String, nullable=False)
    is_teacher = Column(Boolean, default=False)
    telegram_id = Column(Integer, unique=True, nullable=False)        
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    id_in_university =  Column(Integer, unique=True, nullable=True)
    courses = relationship('CourseUser', back_populates='user')

class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    university = Column(String(200))
    semester = Column(String(50))
    teacher_id = Column(Integer, ForeignKey('users.id'))

    # Relationships
    teacher = relationship('User')
    course_users = relationship('CourseUser', back_populates='course')

class CourseUser(Base):
    __tablename__ = 'course_users'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))

    # Relationships
    user = relationship('User', back_populates='courses')



# Database setup
DATABASE_URL = 'sqlite:///corsebot.db'
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
