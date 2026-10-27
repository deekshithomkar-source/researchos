"""Typed extension contracts. Protocols are not implementations or demo agents."""
from typing import Protocol
from pydantic import BaseModel, Field
from app.schemas.research import ResearchRequest, ResearchResult, Source


class AgentContext(BaseModel):
    research_id: str
    request: ResearchRequest
    result: ResearchResult = Field(default_factory=ResearchResult)
    queries: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    sources: list[Source] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class Agent(Protocol):
    async def execute(self, context: AgentContext) -> AgentOutput: ...


class IntentAgent(Agent, Protocol): pass
class PlannerAgent(Agent, Protocol): pass
class SearchAgent(Agent, Protocol): pass
class PaperAgent(Agent, Protocol): pass
class SourceEvaluator(Agent, Protocol): pass
class EvidenceAgent(Agent, Protocol): pass
class GapAgent(Agent, Protocol): pass
class DatasetAgent(Agent, Protocol): pass
class SkillAgent(Agent, Protocol): pass
class CourseAgent(Agent, Protocol): pass
class ProjectAgent(Agent, Protocol): pass
class CareerAgent(Agent, Protocol): pass
class SynthesisAgent(Agent, Protocol): pass
class ReportAgent(Agent, Protocol): pass
