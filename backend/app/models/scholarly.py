from sqlalchemy import Column, Integer, String, Text, ForeignKey, ForeignKeyConstraint, Table
from app.db.database import Base

class ResearchAuthor(Base):
    __tablename__ = 'research_authors'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    author_id = Column(String(64), primary_key=True)
    name = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False)

paper_authors = Table('research_paper_authors', Base.metadata,
    Column('run_id',Integer,primary_key=True), Column('paper_id',String(1024),primary_key=True),
    Column('author_id',String(64),primary_key=True),
    ForeignKeyConstraint(['run_id','paper_id'],['research_papers.run_id','research_papers.paper_id']),
    ForeignKeyConstraint(['run_id','author_id'],['research_authors.run_id','research_authors.author_id']))
