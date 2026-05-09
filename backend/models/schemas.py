from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Issue(BaseModel):
    line: Optional[str] = None
    description: str
    severity: Severity
    suggestion: str


class AgentReview(BaseModel):
    agent_name: str
    issues: List[Issue]
    summary: str
    score: int  # 0-100


class ReviewRequest(BaseModel):
    code: Optional[str] = None
    github_pr_url: Optional[str] = None
    language: Optional[str] = "auto"


class ReviewResponse(BaseModel):
    security: AgentReview
    performance: AgentReview
    logic: AgentReview
    style: AgentReview
    final_recommendation: str
    overall_score: int
    total_issues: int