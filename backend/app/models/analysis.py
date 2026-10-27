"""Run-scoped normalized records; historical research snapshots remain untouched."""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, ForeignKeyConstraint, Table
from app.db.database import Base


class ResearchPaper(Base):
    __tablename__ = 'research_papers'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    paper_id = Column(String(1024), primary_key=True)
    title = Column(Text, nullable=False)
    doi = Column(Text)
    metadata_json = Column(Text, nullable=False)


class ResearchSource(Base):
    __tablename__ = 'research_sources'
    run_id = Column(Integer, primary_key=True)
    source_id = Column(String(64), primary_key=True)
    paper_id = Column(String(1024), nullable=False)
    provider = Column(String(100), nullable=False)
    provider_paper_id = Column(Text, nullable=False)
    url = Column(Text)
    __table_args__ = (ForeignKeyConstraint(['run_id', 'paper_id'], ['research_papers.run_id', 'research_papers.paper_id']),)


class ResearchEvidence(Base):
    __tablename__ = 'research_evidence'
    run_id = Column(Integer, primary_key=True)
    evidence_id = Column(String(64), primary_key=True)
    paper_id = Column(String(1024), nullable=False)
    text = Column(Text, nullable=False)
    locator = Column(String(32), nullable=False)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    source_url = Column(Text)
    kind = Column(String(32), nullable=False)
    __table_args__ = (ForeignKeyConstraint(['run_id', 'paper_id'], ['research_papers.run_id', 'research_papers.paper_id']),)


class ResearchFinding(Base):
    __tablename__ = 'research_findings'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    finding_id = Column(String(64), primary_key=True)
    statement = Column(Text, nullable=False)
    basis = Column(String(64), nullable=False)


class ResearchGap(Base):
    __tablename__ = 'research_gaps'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    gap_id = Column(String(64), primary_key=True)
    statement = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    scope = Column(String(64), nullable=False)


finding_evidence = Table('research_finding_evidence', Base.metadata,
    Column('run_id', Integer, primary_key=True), Column('finding_id', String(64), primary_key=True),
    Column('evidence_id', String(64), primary_key=True),
    ForeignKeyConstraint(['run_id', 'finding_id'], ['research_findings.run_id', 'research_findings.finding_id']),
    ForeignKeyConstraint(['run_id', 'evidence_id'], ['research_evidence.run_id', 'research_evidence.evidence_id']))

gap_evidence = Table('research_gap_evidence', Base.metadata,
    Column('run_id', Integer, primary_key=True), Column('gap_id', String(64), primary_key=True),
    Column('evidence_id', String(64), primary_key=True),
    ForeignKeyConstraint(['run_id', 'gap_id'], ['research_gaps.run_id', 'research_gaps.gap_id']),
    ForeignKeyConstraint(['run_id', 'evidence_id'], ['research_evidence.run_id', 'research_evidence.evidence_id']))


class ResearchReport(Base):
    __tablename__ = 'research_reports'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    content = Column(Text, nullable=False)
    sections_json = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=False)


class ResearchAnalysisRevision(Base):
    __tablename__ = 'research_analysis_revisions'
    run_id = Column(Integer, ForeignKey('research_sessions.id'), primary_key=True)
    revision = Column(String(64), primary_key=True)
    schema_version = Column(Integer, nullable=False)
    payload = Column(Text, nullable=False)
