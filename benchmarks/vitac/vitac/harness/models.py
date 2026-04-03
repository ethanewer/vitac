"""Data models for benchmark results."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from vitac.types import (
    AgentResult,
    FailureMode,
    UnitTestStatus,
    VoiceScoreCard,
)


class TrialResults(BaseModel):
    """Results from a single task trial."""

    id: UUID = Field(default_factory=uuid4)
    trial_name: str
    task_id: str
    instruction: str
    is_resolved: bool | None = None
    failure_mode: FailureMode = FailureMode.UNSET
    parser_results: dict[str, UnitTestStatus] | None = None
    voice_score: VoiceScoreCard = Field(default_factory=VoiceScoreCard)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    trial_started_at: str = ""
    trial_ended_at: str = ""
    agent_started_at: str = ""
    agent_ended_at: str = ""
    test_started_at: str = ""
    test_ended_at: str = ""

    @computed_field
    @property
    def composite_score(self) -> float:
        """Binary score: 1.0 if all tests pass, 0.0 otherwise."""
        return 1.0 if self.is_resolved else 0.0


class BenchmarkResults(BaseModel):
    """Aggregated results from a benchmark run."""

    id: UUID = Field(default_factory=uuid4)
    results: list[TrialResults] = Field(default_factory=list)

    @computed_field
    @property
    def n_resolved(self) -> int:
        return sum(1 for r in self.results if r.is_resolved)

    @computed_field
    @property
    def accuracy(self) -> float:
        if not self.results:
            return 0.0
        return self.n_resolved / len(self.results)

    @computed_field
    @property
    def avg_voice_score(self) -> float:
        scores = [
            r.voice_score.overall
            for r in self.results
            if r.voice_score and r.voice_score.overall > 0
        ]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    @computed_field
    @property
    def avg_naturalness(self) -> float:
        scores = [
            r.voice_score.naturalness
            for r in self.results
            if r.voice_score and r.voice_score.naturalness > 0
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @computed_field
    @property
    def avg_relevance(self) -> float:
        scores = [
            r.voice_score.relevance
            for r in self.results
            if r.voice_score and r.voice_score.relevance > 0
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @computed_field
    @property
    def avg_conciseness(self) -> float:
        scores = [
            r.voice_score.conciseness
            for r in self.results
            if r.voice_score and r.voice_score.conciseness > 0
        ]
        return sum(scores) / len(scores) if scores else 0.0

    @computed_field
    @property
    def resolved_ids(self) -> list[str]:
        return [r.task_id for r in self.results if r.is_resolved]

    @computed_field
    @property
    def avg_composite_score(self) -> float:
        """Average composite score (task_success * voice_quality) across trials."""
        if not self.results:
            return 0.0
        return sum(r.composite_score for r in self.results) / len(self.results)
