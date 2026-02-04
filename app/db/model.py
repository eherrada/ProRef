from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import ForeignKey, LargeBinary
from sqlalchemy.orm import relationship

from app.paths import DB_PATH

Base = declarative_base()

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)


class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(String, primary_key=True)
    jira_key = Column(String, unique=True, nullable=False)
    title = Column(Text)
    description = Column(Text)
    status = Column(String)
    issue_type = Column(String)
    updated_at = Column(DateTime)
    fetched_at = Column(DateTime)
    questions_generated = Column(Boolean, default=False)
    test_cases_generated = Column(Boolean, default=False)
    posted_to_jira = Column(Boolean, default=False)

    generated_content = relationship("GeneratedContent", back_populates="ticket")


class TicketEmbedding(Base):
    __tablename__ = 'ticket_embeddings'

    ticket_id = Column(String, ForeignKey('tickets.id'), primary_key=True)
    embedding = Column(LargeBinary, nullable=False)

    ticket = relationship("Ticket")


class GeneratedContent(Base):
    __tablename__ = 'generated_content'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String, ForeignKey('tickets.id'), nullable=False)
    content_type = Column(String, nullable=False)  # 'questions' | 'test_cases'
    content = Column(Text, nullable=False)  # JSON with questions/tests
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="generated_content")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
